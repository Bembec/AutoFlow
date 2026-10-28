from unittest.mock import patch

import pytest
from sqlalchemy import func, select

from luphina import demo, features
from luphina.storage.db import session_scope
from luphina.storage.models import Approval, Invoice, WorkflowExecution, Workspace

STAFF = "staff@luphina.example"


@pytest.fixture
def staff(client, signup, monkeypatch):
    monkeypatch.setenv("LUPHINA_STAFF_EMAILS", STAFF)
    headers, _ = signup(email=STAFF)
    return headers


# --- feature flags -----------------------------------------------------------------

def test_flags_default_then_environment_then_workspace(monkeypatch):
    workspace = Workspace(name="x", slug="x")
    assert features.enabled("ai_builder", workspace) is True
    assert all(features.all_flags(workspace).values())  # everything is on by default

    monkeypatch.setenv("LUPHINA_FEATURES", "smarter_logic=off, ai_builder=off, nonsense=on")
    assert features.all_flags(workspace)["smarter_logic"] is False
    assert features.all_flags(workspace)["ai_builder"] is False

    features.set_overrides(workspace, {"ai_builder": True})
    assert features.enabled("ai_builder", workspace) is True
    features.set_overrides(workspace, {"ai_builder": None})
    assert features.enabled("ai_builder", workspace) is False
    with pytest.raises(features.UnknownFlag):
        features.enabled("nope", workspace)


def test_staff_switch_features_and_the_server_enforces_them(client, signup, staff):
    headers, workspace_id = signup()
    base = f"/workspaces/{workspace_id}"
    assert client.get(f"{base}/features", headers=headers).json()["ai_builder"] is True

    assert client.put(f"/staff/workspaces/{workspace_id}/features", json={"ai_builder": False},
                      headers=headers).status_code == 403
    flags = client.put(f"/staff/workspaces/{workspace_id}/features",
                       json={"ai_builder": False, "insights_suggestions": False, "connection_checks": False},
                       headers=staff).json()
    assert flags["ai_builder"] is False
    assert client.put(f"/staff/workspaces/{workspace_id}/features", json={"typo": True},
                      headers=staff).status_code == 422

    blocked = client.post(f"{base}/workflows/ai-draft", json={"request": "Invoice every order"}, headers=headers)
    assert blocked.status_code == 403 and "switched off" in blocked.json()["detail"]
    assert client.get(f"{base}/insights", headers=headers).json()["suggestions"] == []
    connection = client.post(f"{base}/connections", json={
        "provider": "smtp", "name": "mailbox",
        "config": {"host": "smtp.example.com", "username": "a@b.co", "from_address": "a@b.co"},
        "secrets": {"password": "app-password-1234"},
    }, headers=headers).json()
    assert client.post(f"{base}/connections/{connection['id']}/check", headers=headers).status_code == 403


# --- demo workspace ----------------------------------------------------------------

def test_demo_workspace_is_complete_safe_and_created_once(client):
    with patch("luphina.integrations.actions.smtplib") as smtp, session_scope() as session:
        workspace, created = demo.seed(session)
        again, created_again = demo.seed(session)
        workspace_id = workspace.id

        assert created and not created_again and again.id == workspace_id
        runs = session.scalar(select(func.count(WorkflowExecution.id)).where(WorkflowExecution.workspace_id == workspace_id))
        invoices = session.scalar(select(func.count(Invoice.id)).where(Invoice.workspace_id == workspace_id))
        waiting = session.scalar(select(func.count(Approval.id)).where(
            Approval.workspace_id == workspace_id, Approval.status == "pending"))
    smtp.SMTP_SSL.assert_not_called()

    assert runs > 60 and invoices > 40 and waiting == 1

    login = client.post("/auth/login", json={"email": demo.DEMO_EMAIL, "password": demo.DEMO_PASSWORD}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    insights = client.get(f"/workspaces/{workspace_id}/insights", headers=headers).json()
    assert insights["last_30_days"]["minutes_saved"] > 0
    assert insights["last_30_days"]["money_saved"] > 0
    assert sum(1 for minutes in insights["weekly_minutes_saved"] if minutes) >= 6
