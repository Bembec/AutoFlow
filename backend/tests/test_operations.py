from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import func, select

from luphina import config, worker
from luphina.storage.db import session_scope
from luphina.storage.models import AccessToken, Workflow, WorkflowExecution


@pytest.fixture
def ws(client, signup):
    headers, workspace_id = signup()
    return client, headers, f"/workspaces/{workspace_id}", workspace_id


# --- health, headers, rate limits ---------------------------------------------

def test_readiness_reports_schema(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["schema"] == "current"


def test_security_headers_and_request_id(client):
    response = client.get("/health", headers={"X-Request-ID": "trace-123"})

    assert response.headers["X-Request-ID"] == "trace-123"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_sign_in_is_rate_limited(client):
    attempts = [
        client.post("/auth/login", json={"email": "x@example.com", "password": "wrong-password"}).status_code
        for _ in range(11)
    ]

    assert attempts[:10] == [401] * 10
    assert attempts[10] == 429


def test_production_refuses_unsafe_settings(monkeypatch):
    monkeypatch.setattr(config, "ENVIRONMENT", "production")
    monkeypatch.setattr(config, "DATABASE_URL", "sqlite:///luphina.db")
    monkeypatch.setattr(config, "PUBLIC_URL", "http://127.0.0.1:8000")
    monkeypatch.delenv("LUPHINA_SECRET_KEYS", raising=False)

    with pytest.raises(config.UnsafeConfiguration) as error:
        config.check_deployment_settings()

    message = str(error.value)
    assert "LUPHINA_SECRET_KEYS" in message
    assert "PostgreSQL" in message
    assert "https" in message


def test_production_accepts_safe_settings(monkeypatch):
    monkeypatch.setattr(config, "ENVIRONMENT", "production")
    monkeypatch.setattr(config, "DATABASE_URL", "postgresql+psycopg://u:p@db/luphina")
    monkeypatch.setattr(config, "PUBLIC_URL", "https://app.luphina.example")
    monkeypatch.setenv("LUPHINA_SECRET_KEYS", "key")
    monkeypatch.delenv("EMAIL_TEST_RECIPIENT", raising=False)

    config.check_deployment_settings()


# --- data ownership -------------------------------------------------------------

def test_export_contains_data_but_never_secrets(ws):
    client, headers, base, _ = ws
    client.post(f"{base}/workflows/from-template", json={"template": "customer-enquiry-triage"}, headers=headers)
    client.post(f"{base}/connections", json={
        "provider": "airtable", "name": "crm", "config": {"base_id": "app1"}, "secrets": {"token": "pat-secret-999999"},
    }, headers=headers)

    response = client.get(f"{base}/export", headers=headers)

    assert response.status_code == 200
    assert "attachment" in response.headers["Content-Disposition"]
    export = response.json()
    assert export["format"] == "luphina-export-v1"
    assert export["workflows"][0]["versions"][0]["definition"]["steps"]
    assert export["connections"][0]["name"] == "crm"
    assert "pat-secret" not in response.text
    assert "encrypted_secrets" not in response.text


def test_export_and_delete_are_owner_only(client, signup):
    owner_headers, workspace_id = signup("owner@example.com")
    admin_headers, _ = signup("admin@example.com")
    base = f"/workspaces/{workspace_id}"
    client.post(f"{base}/members", json={"email": "admin@example.com", "role": "admin"}, headers=owner_headers)

    assert client.get(f"{base}/export", headers=admin_headers).status_code == 403
    assert client.request("DELETE", base, json={"confirm_name": "x"}, headers=admin_headers).status_code == 403


def test_delete_workspace_removes_its_data(ws):
    client, headers, base, workspace_id = ws
    workflow = client.post(f"{base}/workflows/from-template", json={"template": "customer-enquiry-triage"}, headers=headers).json()
    client.post(f"{base}/workflows/{workflow['id']}/executions", json={"mode": "test"}, headers=headers)
    name = client.get("/me", headers=headers).json()["workspaces"][0]["name"]

    assert client.request("DELETE", base, json={"confirm_name": "wrong"}, headers=headers).status_code == 409
    assert client.request("DELETE", base, json={"confirm_name": name}, headers=headers).status_code == 204

    assert client.get(f"{base}/workflows", headers=headers).status_code == 404
    with session_scope() as session:
        assert session.scalar(select(func.count(Workflow.id)).where(Workflow.workspace_id == workspace_id)) == 0
        assert session.scalar(select(func.count(WorkflowExecution.id))) == 0


def test_account_deletion_protects_shared_workspaces(client, signup):
    owner_headers, workspace_id = signup("owner@example.com")
    _, other_workspace = signup("teammate@example.com")
    base = f"/workspaces/{workspace_id}"
    client.post(f"{base}/members", json={"email": "teammate@example.com", "role": "member"}, headers=owner_headers)

    wrong = client.request("DELETE", "/me", json={"password": "nope-nope"}, headers=owner_headers)
    blocked = client.request("DELETE", "/me", json={"password": "correct-horse"}, headers=owner_headers)
    assert wrong.status_code == 403
    assert blocked.status_code == 409

    teammate_id = next(m["user_id"] for m in client.get(f"{base}/members", headers=owner_headers).json()
                       if m["email"] == "teammate@example.com")
    client.patch(f"{base}/members/{teammate_id}", json={"role": "owner"}, headers=owner_headers)

    assert client.request("DELETE", "/me", json={"password": "correct-horse"}, headers=owner_headers).status_code == 204
    assert client.get("/me", headers=owner_headers).status_code == 401
    # The shared workspace survives with its new owner
    with session_scope() as session:
        assert session.scalar(select(func.count(Workflow.id))) == 0
    login = client.post("/auth/login", json={"email": "teammate@example.com", "password": "correct-horse"}).json()
    workspaces = client.get("/me", headers={"Authorization": f"Bearer {login['access_token']}"}).json()["workspaces"]
    assert {w["id"] for w in workspaces} == {workspace_id, other_workspace}


def test_role_changes_are_guarded(client, signup):
    owner_headers, workspace_id = signup("owner@example.com")
    admin_headers, _ = signup("admin@example.com")
    base = f"/workspaces/{workspace_id}"
    client.post(f"{base}/members", json={"email": "admin@example.com", "role": "admin"}, headers=owner_headers)
    members = {m["email"]: m["user_id"] for m in client.get(f"{base}/members", headers=owner_headers).json()}

    # An admin cannot promote to owner or touch the owner
    assert client.patch(f"{base}/members/{members['admin@example.com']}", json={"role": "owner"}, headers=admin_headers).status_code == 409
    assert client.request("DELETE", f"{base}/members/{members['owner@example.com']}", headers=admin_headers).status_code == 409
    # The last owner cannot step down
    assert client.patch(f"{base}/members/{members['owner@example.com']}", json={"role": "member"}, headers=owner_headers).status_code == 409

    assert client.request("DELETE", f"{base}/members/{members['admin@example.com']}", headers=owner_headers).status_code == 204


# --- scheduler ------------------------------------------------------------------

SCHEDULED = {
    "trigger": {"type": "schedule", "schedule": "*/15 * * * *", "sample_payload": {"report": "daily"}},
    "steps": [{"id": "log", "action": "log_activity", "inputs": {"message": "Scheduled {{trigger.scheduled_for}}"}}],
}


def test_invalid_cron_is_rejected(ws):
    client, headers, base, _ = ws
    bad = {**SCHEDULED, "trigger": {"type": "schedule", "schedule": "every tuesday"}}

    response = client.post(f"{base}/workflows", json={"name": "Bad", "definition": bad}, headers=headers)

    assert response.status_code == 422
    assert "Invalid cron" in response.text


def test_scheduler_starts_due_runs_once(ws):
    client, headers, base, _ = ws
    workflow = client.post(f"{base}/workflows", json={"name": "Report", "definition": SCHEDULED}, headers=headers).json()
    client.post(f"{base}/workflows/{workflow['id']}/publish", headers=headers)
    now = datetime(2026, 10, 22, 12, 1, tzinfo=timezone.utc)

    with session_scope() as session:
        first = worker.run_schedules(session, now=now)
    with session_scope() as session:
        again = worker.run_schedules(session, now=now)

    # 10-minute lookback from 12:01 covers the 12:00 slot only
    assert (first, again) == (1, 0)
    execution = client.get(f"{base}/executions", headers=headers).json()[0]
    assert execution["idempotency_key"] == f"schedule:{workflow['id']}:20261022T1200"
    assert execution["trigger_payload"]["report"] == "daily"
    assert execution["status"] == "succeeded"


def test_scheduler_respects_emergency_stop_and_drafts(ws):
    client, headers, base, _ = ws
    draft = client.post(f"{base}/workflows", json={"name": "Draft", "definition": SCHEDULED}, headers=headers).json()
    live = client.post(f"{base}/workflows", json={"name": "Live", "definition": SCHEDULED}, headers=headers).json()
    client.post(f"{base}/workflows/{live['id']}/publish", headers=headers)
    client.post(f"{base}/emergency-stop", headers=headers)
    now = datetime(2026, 10, 22, 12, 1, tzinfo=timezone.utc)

    with session_scope() as session:
        assert worker.run_schedules(session, now=now) == 0

    client.post(f"{base}/resume-automations", headers=headers)
    with session_scope() as session:
        assert worker.run_schedules(session, now=now) == 1
    assert draft["id"] != live["id"]


def test_due_times_lists_every_slot():
    since = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    until = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)

    times = worker.due_times("*/20 * * * *", since, until)

    assert [t.strftime("%H:%M") for t in times] == ["09:20", "09:40", "10:00"]


def test_housekeeping_removes_long_expired_tokens(ws):
    def tokens():
        with session_scope() as session:
            return session.scalar(select(func.count(AccessToken.id)))

    assert tokens() == 1

    with session_scope() as session:
        worker.housekeeping(session)
    assert tokens() == 1  # still valid

    with patch("luphina.worker.utc_now", return_value=datetime(2030, 1, 1, tzinfo=timezone.utc)):
        with session_scope() as session:
            worker.housekeeping(session)
    assert tokens() == 0
