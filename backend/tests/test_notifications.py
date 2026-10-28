from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from luphina import notifications
from luphina.storage.db import session_scope
from luphina.storage.models import Notification


SLACK = {"provider": "slack", "name": "team-slack", "secrets": {"webhook_url": "https://hooks.slack.com/services/T0/B0/xyz"}}
SMTP = {
    "provider": "smtp", "name": "mailbox",
    "config": {"host": "smtp.example.com", "username": "shop@example.com", "from_address": "shop@example.com"},
    "secrets": {"password": "app-password-123"},
}
SEND = {"id": "send", "action": "send_email", "inputs": {"to": "a@b.co", "subject": "s", "body": "b"}}
FAILING = {"id": "quote", "action": "exchange_rate_quote", "inputs": {"amount_eur": 10}}


@pytest.fixture(autouse=True)
def fakes():
    with (
        patch("luphina.engine.executor.sleep"),
        patch("luphina.engine.actions.fetch_eur_to_usd", return_value=(None, None)),
    ):
        yield


@pytest.fixture
def ws(client, signup):
    headers, workspace_id = signup()
    base = f"/workspaces/{workspace_id}"
    client.post(f"{base}/connections", json=SLACK, headers=headers)
    client.patch(f"{base}/notifications", json={"notify_slack_connection": "team-slack"}, headers=headers)
    return client, headers, base


def queued():
    with session_scope() as session:
        return [(n.kind, n.subject, n.link) for n in session.scalars(select(Notification).order_by(Notification.id))]


def run(ws, steps, mode="live"):
    client, headers, base = ws
    workflow = client.post(f"{base}/workflows", json={"name": "Shop flow", "definition": {"steps": steps}}, headers=headers).json()
    client.post(f"{base}/workflows/{workflow['id']}/publish", headers=headers)
    return client.post(f"{base}/workflows/{workflow['id']}/executions", json={"mode": mode}, headers=headers).json()


def test_approval_waiting_is_notified(ws):
    run(ws, [SEND])

    kind, subject, link = queued()[0]
    assert kind == "approval"
    assert subject == 'Shop flow: please approve "send"'
    assert "/approvals?focus=" in link


def test_live_failures_are_notified_but_test_runs_are_not(ws):
    run(ws, [FAILING], mode="test")
    assert queued() == []

    execution = run(ws, [FAILING])

    kind, subject, link = queued()[0]
    assert kind == "failure"
    assert subject == f"Shop flow: run #{execution['id']} failed"
    assert link.endswith(f"/executions/{execution['id']}")


def test_notification_kinds_can_be_turned_off(ws):
    client, headers, base = ws
    client.patch(f"{base}/notifications", json={"notify_on_approval": False, "notify_on_failure": False}, headers=headers)

    run(ws, [SEND])
    run(ws, [FAILING])

    assert queued() == []


def test_no_channel_means_nothing_is_queued(client, signup):
    headers, workspace_id = signup("quiet@example.com")
    base = f"/workspaces/{workspace_id}"

    run((client, headers, base), [SEND])

    assert queued() == []
    assert client.post(f"{base}/notifications/test", headers=headers).status_code == 409


def test_slack_url_must_be_a_slack_webhook(ws):
    client, headers, base = ws
    bad = {**SLACK, "name": "bad", "secrets": {"webhook_url": "https://evil.example/hook"}}

    response = client.post(f"{base}/connections", json=bad, headers=headers)

    assert response.status_code == 409
    assert "hooks.slack.com" in response.json()["detail"]


def test_worker_delivers_to_slack(ws):
    client, headers, base = ws
    client.post(f"{base}/notifications/test", headers=headers)

    with patch("luphina.notifications.requests.post") as post:
        post.return_value = MagicMock(status_code=200)
        with session_scope() as session:
            assert notifications.deliver_pending(session) == 1
        with session_scope() as session:
            assert notifications.deliver_pending(session) == 0  # not sent twice

    url = post.call_args.args[0]
    assert url == "https://hooks.slack.com/services/T0/B0/xyz"
    assert "Test notification" in post.call_args.kwargs["json"]["text"]


def test_failed_delivery_is_retried_then_given_up(ws):
    client, headers, base = ws
    client.post(f"{base}/notifications/test", headers=headers)

    with patch("luphina.notifications.requests.post") as post:
        post.return_value = MagicMock(status_code=500)
        for _ in range(notifications.MAX_ATTEMPTS + 2):
            with session_scope() as session:
                notifications.deliver_pending(session)

    assert post.call_count == notifications.MAX_ATTEMPTS
    with session_scope() as session:
        notification = session.scalars(select(Notification)).one()
        assert notification.sent_at is None
        assert "slack: Slack returned 500" in notification.last_error


def test_email_notifications_use_the_workspace_mailbox(ws, monkeypatch):
    client, headers, base = ws
    monkeypatch.setenv("EMAIL_SEND_ENABLED", "true")
    client.post(f"{base}/connections", json=SMTP, headers=headers)
    client.patch(f"{base}/notifications", json={
        "notify_email": "owner@shop.example", "notify_smtp_connection": "mailbox", "notify_slack_connection": "",
    }, headers=headers)
    client.post(f"{base}/notifications/test", headers=headers)

    with patch("luphina.notifications.smtplib") as smtp:
        with session_scope() as session:
            assert notifications.deliver_pending(session) == 1

    server = smtp.SMTP_SSL.return_value.__enter__.return_value
    server.login.assert_called_once_with("shop@example.com", "app-password-123")
    message = server.send_message.call_args.args[0]
    assert message["To"] == "owner@shop.example"
    assert message["Subject"] == "[Luphina] Test notification"
