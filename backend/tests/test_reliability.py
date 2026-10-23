import smtplib
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select, update

from autoflow.engine.templates_ecommerce import SAMPLE_SHOPIFY_ORDER
from autoflow.storage.db import engine as db_engine
from autoflow.storage.db import session_scope
from autoflow.storage.models import Notification, StepExecution, WorkflowExecution, Workspace


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("autoflow.engine.executor.sleep"):
        yield


@pytest.fixture
def ws(client, signup):
    headers, workspace_id = signup()
    return client, headers, f"/workspaces/{workspace_id}", workspace_id


def flow(ws, steps):
    client, headers, base, _ = ws
    workflow = client.post(f"{base}/workflows", json={"name": "F", "definition": {"steps": steps}}, headers=headers).json()
    client.post(f"{base}/workflows/{workflow['id']}/publish", headers=headers)
    return workflow


def start(ws, workflow, payload=None, mode="live"):
    client, headers, base, _ = ws
    return client.post(f"{base}/workflows/{workflow['id']}/executions",
                       json={"mode": mode, "payload": payload or {}}, headers=headers).json()


# --- compensation: voiding invoices ---------------------------------------------

def test_invoices_can_be_voided_from_the_app_and_by_a_workflow(ws):
    client, headers, base, _ = ws
    issue = flow(ws, [{"id": "invoice", "action": "create_invoice", "inputs": {"order": "{{trigger}}"}}])
    start(ws, issue, SAMPLE_SHOPIFY_ORDER)
    second = start(ws, issue, {**SAMPLE_SHOPIFY_ORDER, "id": 42, "name": "#1002"})
    assert second["status"] == "succeeded"

    listed = client.get(f"{base}/invoices", headers=headers).json()
    first_id = next(i["id"] for i in listed if i["order"] == str(SAMPLE_SHOPIFY_ORDER["id"]))

    voided = client.post(f"{base}/invoices/{first_id}/void", json={"reason": "Customer cancelled"}, headers=headers)
    assert voided.status_code == 200 and voided.json()["void_reason"] == "Customer cancelled"
    again = client.post(f"{base}/invoices/{first_id}/void", json={"reason": "Other"}, headers=headers).json()
    assert again["void_reason"] == "Customer cancelled"  # voiding twice changes nothing

    page = client.get("/invoices/" + next(i for i in listed if i["id"] == first_id)["url"].rsplit("/", 1)[1])
    assert "VOID" in page.text and "Customer cancelled" in page.text

    # A refund workflow voids by order id
    refund = flow(ws, [{"id": "void", "action": "void_invoice",
                        "inputs": {"order_ref": "{{trigger.id}}", "reason": "Refunded"}}])
    done = start(ws, refund, {"id": 42})
    assert done["status"] == "succeeded", done["error"]
    assert done["steps"][0]["output"]["voided"] is True
    assert start(ws, refund, {"id": 42})["steps"][0]["output"]["voided"] is False
    assert start(ws, refund, {"id": 777})["steps"][0]["output"] == {"voided": False, "found": False}

    statuses = {i["order"]: i["void_reason"] for i in client.get(f"{base}/invoices", headers=headers).json()}
    assert statuses == {str(SAMPLE_SHOPIFY_ORDER["id"]): "Customer cancelled", "42": "Refunded"}


def test_viewers_cannot_void(ws, client, signup):
    _, headers, base, _ = ws
    viewer, _ = signup(email="viewer@example.com")
    client.post(f"{base}/members", json={"email": "viewer@example.com", "role": "viewer"}, headers=headers)
    assert client.post(f"{base}/invoices/1/void", json={"reason": "no"}, headers=viewer).status_code == 403


# --- compensation: confirming an uncertain step ---------------------------------

def test_confirm_done_continues_without_repeating_the_step(ws):
    client, headers, base, _ = ws
    workflow = flow(ws, [
        {"id": "send", "action": "send_email", "inputs": {"to": "a@b.co", "subject": "s", "body": "b"}},
        {"id": "after", "action": "log_activity", "inputs": {"message": "after the email"}},
    ])
    with patch("autoflow.engine.actions.send_email", return_value=True) as send:
        execution = start(ws, workflow)
        # The worker died while sending: the step is "running", outcome unknown
        with db_engine.begin() as connection:
            connection.execute(update(StepExecution).where(StepExecution.execution_id == execution["id"],
                                                           StepExecution.step_id == "send")
                               .values(status="running", attempts=1))
            connection.execute(update(WorkflowExecution).where(WorkflowExecution.id == execution["id"])
                               .values(status="running"))
        from autoflow.engine import executor
        with session_scope() as session:
            executor.execute(session, session.get(WorkflowExecution, execution["id"]))
        assert client.get(f"{base}/executions/{execution['id']}", headers=headers).json()["status"] == "needs_attention"

        done = client.post(f"{base}/executions/{execution['id']}/confirm-done", headers=headers).json()
        send.assert_not_called()

    assert done["status"] == "succeeded"
    steps = {s["step_id"]: s for s in done["steps"]}
    assert steps["send"]["output"] == {"confirmed_by_person": True}
    assert steps["after"]["status"] == "succeeded"
    assert client.post(f"{base}/executions/{execution['id']}/confirm-done", headers=headers).status_code == 409


# --- connection health ------------------------------------------------------------

def add_smtp(ws, name="mailbox"):
    client, headers, base, _ = ws
    return client.post(f"{base}/connections", json={
        "provider": "smtp", "name": name,
        "config": {"host": "smtp.example.com", "username": "me@shop.example", "from_address": "me@shop.example"},
        "secrets": {"password": "app-password-1234"},
    }, headers=headers).json()


def enable_alerts(ws):
    _, _, _, workspace_id = ws
    with session_scope() as session:
        session.execute(update(Workspace).where(Workspace.id == workspace_id)
                        .values(notify_email="owner@shop.example", notify_smtp_connection="alerts"))


def test_check_marks_bad_credentials_and_alerts_once(ws):
    client, headers, base, workspace_id = ws
    connection = add_smtp(ws)
    enable_alerts(ws)

    with patch("autoflow.integrations.health.smtplib.SMTP_SSL") as smtp:
        smtp.return_value.__enter__.return_value.login.side_effect = smtplib.SMTPAuthenticationError(535, b"bad")
        first = client.post(f"{base}/connections/{connection['id']}/check", headers=headers).json()
        client.post(f"{base}/connections/{connection['id']}/check", headers=headers)

    assert first["ok"] is False and first["status"] == "error"
    assert "rejected the login" in first["message"] and first["last_checked_at"]
    with session_scope() as session:
        alerts = session.scalars(select(Notification).where(Notification.workspace_id == workspace_id)).all()
    assert len(alerts) == 1 and "Reconnect" in alerts[0].subject

    # Fixing the password and checking again brings it back
    client.put(f"{base}/connections/{connection['id']}/secrets", json={"secrets": {"password": "new-password-567"}},
               headers=headers)
    with patch("autoflow.integrations.health.smtplib.SMTP_SSL"):
        fixed = client.post(f"{base}/connections/{connection['id']}/check", headers=headers).json()
    assert fixed == {**fixed, "ok": True, "status": "active"}


def test_network_trouble_does_not_mark_a_connection_broken(ws):
    client, headers, base, _ = ws
    connection = add_smtp(ws)
    with patch("autoflow.integrations.health.smtplib.SMTP_SSL", side_effect=OSError("timed out")):
        result = client.post(f"{base}/connections/{connection['id']}/check", headers=headers).json()
    assert result["ok"] is False and result["status"] == "active"
    assert "Could not reach" in result["message"]


def test_api_connections_are_checked_with_read_only_calls(ws):
    client, headers, base, _ = ws
    shop = client.post(f"{base}/connections", json={
        "provider": "shopify", "name": "store", "config": {"shop_domain": "mug-shop.myshopify.com"},
        "secrets": {"access_token": "shpat_0123456789abcdef"},
    }, headers=headers).json()
    slack = client.post(f"{base}/connections", json={
        "provider": "slack", "name": "team", "secrets": {"webhook_url": "https://hooks.slack.com/services/T0/B0/xyz"},
    }, headers=headers).json()

    with patch("autoflow.integrations.health.requests.get", return_value=MagicMock(status_code=401)) as get:
        result = client.post(f"{base}/connections/{shop['id']}/check", headers=headers).json()
    assert get.call_args.args[0] == "https://mug-shop.myshopify.com/admin/api/2025-07/shop.json"
    assert result["ok"] is False and "Shopify rejected" in result["message"]

    unchecked = client.post(f"{base}/connections/{slack['id']}/check", headers=headers).json()
    assert unchecked["ok"] is None and unchecked["status"] == "active"
