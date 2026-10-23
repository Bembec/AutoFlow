from datetime import timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select, update

from autoflow.engine import limits
from autoflow.security import outbound
from autoflow.storage.db import session_scope, utc_now
from autoflow.storage.models import AuditEvent, Workspace

STAFF = "staff@autoflow.example"
PHISHING = "Your account will be locked. Please verify your password at http://login-check.example/now"


@pytest.fixture
def ws(client, signup):
    headers, workspace_id = signup()
    base = f"/workspaces/{workspace_id}"
    client.post(f"{base}/connections", json={
        "provider": "smtp", "name": "mailbox",
        "config": {"host": "smtp.example.com", "username": "me@shop.example", "from_address": "me@shop.example"},
        "secrets": {"password": "app-password-1234"},
    }, headers=headers)
    return client, headers, base, workspace_id


@pytest.fixture
def staff(client, signup, monkeypatch):
    monkeypatch.setenv("AUTOFLOW_STAFF_EMAILS", STAFF)
    headers, _ = signup(email=STAFF)
    return headers


def email_flow(ws, body):
    client, headers, base, _ = ws
    workflow = client.post(f"{base}/workflows", json={"name": "Mail", "definition": {"steps": [{
        "id": "send", "action": "smtp_send_email",
        "inputs": {"connection": "mailbox", "to": "ada@example.com", "subject": "Hello", "body": body},
    }]}}, headers=headers).json()
    client.post(f"{base}/workflows/{workflow['id']}/publish", headers=headers)
    return workflow


def run(ws, workflow, mode):
    client, headers, base, _ = ws
    return client.post(f"{base}/workflows/{workflow['id']}/executions", json={"mode": mode}, headers=headers).json()


# --- outbound content checks ---------------------------------------------------

def test_ordinary_shop_emails_pass():
    assert outbound.check_email({"to": "ada@example.com", "subject": "Your invoice INV-12",
                                 "body": "Thanks for your order! https://shop.example/invoices/abc"}) == []
    # A failed-payment email may ask for card details: warned, not blocked
    findings = outbound.check_email({"to": "a@example.com", "subject": "Payment failed",
                                     "body": "Please update your card details at https://shop.example/account"})
    assert [f["level"] for f in findings] == ["warn"]


def test_phishing_is_blocked_before_approval_and_logged(ws):
    workflow = email_flow(ws, PHISHING)
    execution = run(ws, workflow, "live")

    assert execution["status"] == "failed"
    assert "blocked by the safety check" in execution["error"]
    client, headers, base, workspace_id = ws
    assert client.get(f"{base}/approvals", headers=headers).json() == []
    with session_scope() as session:
        event = session.scalar(select(AuditEvent).where(AuditEvent.action == "outbound.blocked"))
        assert event.workspace_id == workspace_id


def test_risky_email_warns_the_approver(ws):
    workflow = email_flow(ws, "Spring sale! https://bit.ly/spring-sale")
    client, headers, base, _ = ws

    tested = run(ws, workflow, "test")
    assert tested["status"] == "succeeded"
    assert "link shortener" in tested["steps"][0]["output"]["safety_warnings"][0]

    run(ws, workflow, "live")
    approval = client.get(f"{base}/approvals", headers=headers).json()[0]
    assert "link shortener" in approval["payload"]["safety_warnings"][0]


def test_sent_email_carries_abuse_headers(ws, monkeypatch):
    monkeypatch.setenv("EMAIL_SEND_ENABLED", "true")
    workflow = email_flow(ws, "Thanks for your order.")
    client, headers, base, workspace_id = ws
    run(ws, workflow, "live")
    approval = client.get(f"{base}/approvals", headers=headers).json()[0]

    with patch("autoflow.integrations.actions.smtplib") as smtp:
        client.post(f"{base}/approvals/{approval['id']}/approve", headers=headers)

    done = client.get(f"{base}/executions", headers=headers).json()[0]
    detail = client.get(f"{base}/executions/{done['id']}", headers=headers).json()
    assert done["status"] == "succeeded", (detail["error"], [s["error"] for s in detail["steps"]])
    message = smtp.SMTP_SSL.return_value.__enter__.return_value.send_message.call_args.args[0]
    assert message["X-AutoFlow-Workspace"] == str(workspace_id)
    assert message["X-Report-Abuse"].endswith(f"/report-abuse?workspace={workspace_id}")


# --- new-account limits -----------------------------------------------------

def test_new_accounts_get_lower_limits_until_trusted(ws, staff):
    client, headers, base, workspace_id = ws
    dashboard = client.get(f"{base}/dashboard", headers=headers).json()
    assert dashboard["limits"] == {"executions": 200, "ai_calls": 50, "emails": 20}
    assert dashboard["new_account_until"] is not None

    assert client.post(f"/staff/workspaces/{workspace_id}/trust", headers=headers).status_code == 403
    assert client.post(f"/staff/workspaces/{workspace_id}/trust", headers=staff).status_code == 200
    dashboard = client.get(f"{base}/dashboard", headers=headers).json()
    assert dashboard["limits"] == {"executions": 1000, "ai_calls": 200, "emails": 100}
    assert dashboard["new_account_until"] is None


def test_new_account_limits_end_after_a_week(ws):
    client, headers, base, workspace_id = ws
    with session_scope() as session:
        session.execute(update(Workspace).where(Workspace.id == workspace_id)
                        .values(created_at=utc_now() - timedelta(days=limits.NEW_ACCOUNT_DAYS, minutes=1)))
    assert client.get(f"{base}/dashboard", headers=headers).json()["new_account_until"] is None


def test_new_account_email_limit_says_why(ws):
    client, headers, base, workspace_id = ws
    with session_scope() as session:
        workspace = session.get(Workspace, workspace_id)
        with patch.object(limits, "usage_today", return_value={"executions": 0, "ai_calls": 0, "emails": 20}):
            with pytest.raises(limits.LimitReached, match="new accounts"):
                limits.check_can_run_step(session, workspace, "smtp_send_email", "live")


# --- AI budget ----------------------------------------------------------------

def test_monthly_ai_budget_is_a_hard_cap(client, signup, monkeypatch):
    monkeypatch.setenv("AUTOFLOW_AI_COST_PER_CALL_USD", "0.5")
    headers, workspace_id = signup(plan="free")  # budget $2 = 4 calls

    with session_scope() as session:
        workspace = session.get(Workspace, workspace_id)
        for _ in range(4):
            limits.use_ai_call(session, workspace, "document")
        with pytest.raises(limits.LimitReached, match="AI budget"):
            limits.use_ai_call(session, workspace, "document")

    bill = client.get(f"/workspaces/{workspace_id}/billing", headers=headers).json()
    assert bill["ai"] == {"calls": 4, "estimated_cost_usd": 2.0, "budget_usd": 2, "cost_per_call_usd": 0.5}
    assert any("AI budget" in alert for alert in bill["alerts"])


def test_runs_report_their_ai_cost(ws):
    workflow = email_flow(ws, "Thanks for your order.")
    execution = run(ws, workflow, "test")
    assert execution["ai_calls"] == 0 and execution["ai_cost_usd"] == 0


# --- abuse reports and suspension ----------------------------------------------

def test_abuse_reports_reach_staff_and_are_rate_limited(client, ws, staff):
    _, headers, _, workspace_id = ws
    report = {"category": "phishing", "message": "This email asked for my bank password.", "workspace_id": workspace_id}

    assert client.post("/abuse-reports", json=report).status_code == 201
    for _ in range(4):
        client.post("/abuse-reports", json={**report, "workspace_id": 99999})
    assert client.post("/abuse-reports", json=report).status_code == 429

    assert client.get("/staff/abuse-reports", headers=headers).status_code == 403
    reports = client.get("/staff/abuse-reports", headers=staff).json()
    assert len(reports) == 5 and reports[-1]["workspace_id"] == workspace_id
    assert "99999 was not found" in reports[0]["message"]

    closed = client.post(f"/staff/abuse-reports/{reports[0]['id']}/close", headers=staff).json()
    assert closed["status"] == "closed"


def test_staff_suspension_cannot_be_lifted_by_the_owner(client, ws, staff):
    _, headers, base, workspace_id = ws
    client.post(f"/staff/workspaces/{workspace_id}/suspend", json={"reason": "Phishing reports."}, headers=staff)

    assert client.get(f"{base}/dashboard", headers=headers).json()["automation_paused"] is True
    refused = client.post(f"{base}/resume-automations", headers=headers)
    assert refused.status_code == 403 and "Phishing reports." in refused.json()["detail"]

    client.post(f"/staff/workspaces/{workspace_id}/unsuspend", headers=staff)
    assert client.get(f"{base}/dashboard", headers=headers).json()["automation_paused"] is False
