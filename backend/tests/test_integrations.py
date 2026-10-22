import base64
import hashlib
import hmac
import json
import socket
import time
from unittest.mock import MagicMock, patch

import pytest

from autoflow.integrations import webhooks
from autoflow.security import net, vault


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("autoflow.engine.executor.sleep"):
        yield


@pytest.fixture
def ws(client, signup):
    headers, workspace_id = signup()
    return client, headers, f"/workspaces/{workspace_id}"


def fake_response(status=200, payload=None):
    response = MagicMock()
    response.status_code = status
    response.ok = status < 400
    response.json.return_value = payload or {}
    response.text = json.dumps(payload or {})
    return response


def create_workflow(ws, steps, trigger=None, publish=True):
    client, headers, base = ws
    definition = {"steps": steps}
    if trigger:
        definition["trigger"] = trigger
    workflow = client.post(
        f"{base}/workflows", json={"name": "Flow", "definition": definition}, headers=headers
    ).json()
    if publish:
        client.post(f"{base}/workflows/{workflow['id']}/publish", headers=headers)
    return workflow


def run_live(ws, workflow_id, payload=None):
    client, headers, base = ws
    return client.post(
        f"{base}/workflows/{workflow_id}/executions",
        json={"mode": "live", "payload": payload or {}},
        headers=headers,
    ).json()


AIRTABLE = {
    "provider": "airtable",
    "name": "crm",
    "config": {"base_id": "appBASE"},
    "secrets": {"token": "patSECRET-TOKEN-123456"},
}


# --- vault ------------------------------------------------------------------

def test_vault_round_trip_and_mask():
    token = vault.encrypt_json({"password": "hunter2-long-secret"})

    assert "hunter2" not in token
    assert vault.decrypt_json(token) == {"password": "hunter2-long-secret"}
    assert vault.mask("patSECRET-TOKEN-123456") == "pat…3456"


def test_vault_key_rotation(monkeypatch):
    old_key, new_key = vault.generate_key(), vault.generate_key()

    monkeypatch.setenv("AUTOFLOW_SECRET_KEYS", old_key)
    vault._fernet.cache_clear()
    token = vault.encrypt_json({"a": 1})

    # New primary key first; the old key still decrypts
    monkeypatch.setenv("AUTOFLOW_SECRET_KEYS", f"{new_key},{old_key}")
    vault._fernet.cache_clear()
    assert vault.decrypt_json(token) == {"a": 1}
    rotated = vault.rotate(token)

    monkeypatch.setenv("AUTOFLOW_SECRET_KEYS", new_key)
    vault._fernet.cache_clear()
    assert vault.decrypt_json(rotated) == {"a": 1}
    with pytest.raises(vault.VaultError):
        vault.decrypt_json(token)

    monkeypatch.delenv("AUTOFLOW_SECRET_KEYS")
    vault._fernet.cache_clear()


# --- connections ------------------------------------------------------------

def test_connection_secrets_are_never_returned(ws):
    client, headers, base = ws

    created = client.post(f"{base}/connections", json=AIRTABLE, headers=headers)
    listed = client.get(f"{base}/connections", headers=headers)

    assert created.status_code == 201
    assert "patSECRET-TOKEN-123456" not in created.text + listed.text
    assert listed.json()[0]["secrets"]["token"] == "pat…3456"


def test_connection_validation_and_roles(client, signup):
    owner_headers, workspace_id = signup("owner@example.com")
    member_headers, _ = signup("member@example.com")
    base = f"/workspaces/{workspace_id}"
    client.post(f"{base}/members", json={"email": "member@example.com", "role": "member"}, headers=owner_headers)

    # Only admins manage credentials
    assert client.post(f"{base}/connections", json=AIRTABLE, headers=member_headers).status_code == 403

    bad = {**AIRTABLE, "config": {}}
    assert "Missing config: base_id" in client.post(f"{base}/connections", json=bad, headers=owner_headers).text

    oauth_only = {"provider": "google", "name": "g", "secrets": {"access_token": "x"}}
    assert client.post(f"{base}/connections", json=oauth_only, headers=owner_headers).status_code == 409

    client.post(f"{base}/connections", json=AIRTABLE, headers=owner_headers)
    assert client.post(f"{base}/connections", json=AIRTABLE, headers=owner_headers).status_code == 409


def test_revoked_connection_cannot_be_used(ws):
    client, headers, base = ws
    connection = client.post(f"{base}/connections", json=AIRTABLE, headers=headers).json()
    client.delete(f"{base}/connections/{connection['id']}", headers=headers)

    workflow = create_workflow(ws, [{
        "id": "save", "action": "airtable_upsert",
        "inputs": {"connection": "crm", "table": "Customers", "fields": {"Email": "a@b.co"}},
    }])
    execution = run_live(ws, workflow["id"])

    assert execution["status"] == "failed"
    assert "No connection named 'crm'" in execution["error"]


# --- connector actions --------------------------------------------------------

def test_airtable_upsert_uses_the_workspace_connection(ws):
    client, headers, base = ws
    client.post(f"{base}/connections", json=AIRTABLE, headers=headers)
    workflow = create_workflow(ws, [{
        "id": "save", "action": "airtable_upsert",
        "inputs": {"connection": "crm", "table": "Customers",
                   "fields": {"Email": "{{trigger.email}}", "Name": "{{trigger.name}}"}},
    }])

    with patch("autoflow.integrations.actions.requests") as http:
        http.get.return_value = fake_response(200, {"records": []})
        http.post.return_value = fake_response(200, {"id": "rec123"})
        execution = run_live(ws, workflow["id"], {"email": "ada@example.com", "name": "Ada"})

    assert execution["status"] == "succeeded"
    assert execution["steps"][0]["output"] == {"record_id": "rec123", "operation": "created"}
    sent_headers = http.post.call_args.kwargs["headers"]
    assert sent_headers["Authorization"] == "Bearer patSECRET-TOKEN-123456"
    assert "appBASE" in http.post.call_args.args[0]
    # The decrypted secret is never stored in the execution record
    assert "patSECRET" not in json.dumps(execution)


def test_connections_do_not_leak_between_workspaces(ws, signup):
    client, headers, base = ws
    client.post(f"{base}/connections", json=AIRTABLE, headers=headers)

    other_headers, other_workspace = signup("other@example.com")
    other = (client, other_headers, f"/workspaces/{other_workspace}")
    workflow = create_workflow(other, [{
        "id": "save", "action": "airtable_upsert",
        "inputs": {"connection": "crm", "table": "Customers", "fields": {"Email": "x@y.co"}},
    }])

    with patch("autoflow.integrations.actions.requests") as http:
        execution = run_live(other, workflow["id"])

    assert execution["status"] == "failed"
    assert "No connection named 'crm'" in execution["error"]
    http.get.assert_not_called()


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8000/admin",
    "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.5/",
    "file:///etc/passwd",
    "http://user:pass@example.com/",
])
def test_http_actions_refuse_internal_addresses(ws, url):
    workflow = create_workflow(ws, [{"id": "get", "action": "http_get", "inputs": {"url": url}, "retry": {"max_attempts": 3}}])

    with patch("autoflow.integrations.actions.requests") as http:
        execution = run_live(ws, workflow["id"])

    assert execution["status"] == "failed"
    assert execution["steps"][0]["attempts"] == 1
    http.request.assert_not_called()


def test_public_url_check_resolves_dns():
    public = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
    private = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.10", 443))]

    with patch("autoflow.security.net.socket.getaddrinfo", return_value=public):
        assert net.check_public_url("https://api.example.com/x")

    # A public-looking name that resolves inside the network is refused
    with patch("autoflow.security.net.socket.getaddrinfo", return_value=private):
        with pytest.raises(net.UnsafeURL):
            net.check_public_url("https://sneaky.example.com/x")


def test_http_get_with_api_key_connection(ws):
    client, headers, base = ws
    client.post(f"{base}/connections", json={
        "provider": "http", "name": "shop-api",
        "config": {"header_name": "X-Api-Key", "base_url": "https://api.example.com/v1"},
        "secrets": {"header_value": "key-abcdef-123456"},
    }, headers=headers)
    workflow = create_workflow(ws, [{
        "id": "get", "action": "http_get", "inputs": {"connection": "shop-api", "url": "/orders"},
    }])

    with (
        patch("autoflow.integrations.actions.check_public_url"),
        patch("autoflow.integrations.actions.requests") as http,
    ):
        http.request.return_value = fake_response(200, {"orders": [1, 2]})
        execution = run_live(ws, workflow["id"])

    assert execution["steps"][0]["output"]["body"] == {"orders": [1, 2]}
    method, url = http.request.call_args.args
    assert (method, url) == ("GET", "https://api.example.com/v1/orders")
    assert http.request.call_args.kwargs["headers"]["X-Api-Key"] == "key-abcdef-123456"
    assert http.request.call_args.kwargs["allow_redirects"] is False


def test_smtp_send_needs_approval_and_respects_switch(ws, monkeypatch):
    client, headers, base = ws
    client.post(f"{base}/connections", json={
        "provider": "smtp", "name": "mailbox",
        "config": {"host": "smtp.example.com", "username": "me@shop.example", "from_address": "me@shop.example"},
        "secrets": {"password": "app-password-1234"},
    }, headers=headers)
    workflow = create_workflow(ws, [{
        "id": "send", "action": "smtp_send_email",
        "inputs": {"connection": "mailbox", "to": "ada@example.com", "subject": "Hi", "body": "Hello"},
    }])

    execution = run_live(ws, workflow["id"])
    assert execution["status"] == "waiting_approval"

    approval = client.get(f"{base}/approvals", params={"kind": "step"}, headers=headers).json()[0]
    with patch("autoflow.integrations.actions.smtplib") as smtp:
        client.post(f"{base}/approvals/{approval['id']}/approve", headers=headers)

    done = client.get(f"{base}/executions/{execution['id']}", headers=headers).json()
    assert done["status"] == "failed"
    assert "EMAIL_SEND_ENABLED" in done["error"]
    smtp.SMTP_SSL.assert_not_called()


# --- OAuth ------------------------------------------------------------------

@pytest.fixture
def google_oauth(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id-123")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret-456")


def connect_google(ws, expires_in=3600):
    client, headers, base = ws
    start = client.post(f"{base}/connections/oauth/google/start", json={"name": "sheets"}, headers=headers).json()
    state = start["authorization_url"].split("state=")[1].split("&")[0]

    from urllib.parse import unquote

    with patch("autoflow.integrations.oauth.requests") as http:
        http.post.return_value = fake_response(200, {
            "access_token": "access-1", "refresh_token": "refresh-1", "expires_in": expires_in,
        })
        callback = client.get("/oauth/callback/google", params={"code": "abc", "state": unquote(state)})

    return start, callback


def test_oauth_not_configured(ws):
    client, headers, base = ws

    response = client.post(f"{base}/connections/oauth/google/start", json={"name": "g"}, headers=headers)

    assert response.status_code == 409
    assert "GOOGLE_CLIENT_ID" in response.json()["detail"]


def test_oauth_connect_flow(ws, google_oauth):
    client, headers, base = ws

    start, callback = connect_google(ws)

    assert "client_id=client-id-123" in start["authorization_url"]
    assert "access_type=offline" in start["authorization_url"]
    assert callback.json() == {"connected": True, "connection": "sheets", "provider": "google"}
    listed = client.get(f"{base}/connections", headers=headers).json()
    assert listed[0]["provider"] == "google"
    assert "access-1" not in json.dumps(listed)


def test_oauth_rejects_tampered_state(ws, google_oauth):
    client, _, _ = ws

    response = client.get("/oauth/callback/google", params={"code": "abc", "state": "forged"})

    assert response.status_code == 400
    assert "invalid or has expired" in response.json()["detail"]


def test_expired_token_is_refreshed_before_use(ws, google_oauth):
    client, headers, base = ws
    connect_google(ws, expires_in=0)
    workflow = create_workflow(ws, [{
        "id": "row", "action": "google_sheets_append_row",
        "inputs": {"connection": "sheets", "spreadsheet_id": "sheet-1", "values": ["{{trigger.name}}", 1]},
    }])

    with (
        patch("autoflow.integrations.connections.requests") as refresh_http,
        patch("autoflow.integrations.actions.requests") as sheets_http,
    ):
        refresh_http.post.return_value = fake_response(200, {"access_token": "access-2", "expires_in": 3600})
        sheets_http.post.return_value = fake_response(200, {"updates": {"updatedRange": "Sheet1!A2:B2"}})
        execution = run_live(ws, workflow["id"], {"name": "Ada"})

    assert execution["status"] == "succeeded"
    assert refresh_http.post.call_args.kwargs["data"]["refresh_token"] == "refresh-1"
    assert sheets_http.post.call_args.kwargs["headers"]["Authorization"] == "Bearer access-2"
    assert sheets_http.post.call_args.kwargs["json"] == {"values": [["Ada", 1]]}


def test_revoked_refresh_token_marks_connection_for_reconnect(ws, google_oauth):
    client, headers, base = ws
    connect_google(ws, expires_in=0)
    workflow = create_workflow(ws, [{
        "id": "row", "action": "google_sheets_append_row",
        "inputs": {"connection": "sheets", "spreadsheet_id": "s", "values": [1]},
    }])

    with patch("autoflow.integrations.connections.requests") as refresh_http:
        refresh_http.post.return_value = fake_response(400, {"error": "invalid_grant"})
        execution = run_live(ws, workflow["id"])

    assert execution["status"] == "failed"
    assert "needs reconnecting" in execution["error"]
    assert client.get(f"{base}/connections", headers=headers).json()[0]["status"] == "error"


# --- webhooks ---------------------------------------------------------------

WEBHOOK_STEPS = [{"id": "log", "action": "log_activity", "inputs": {"message": "Order {{trigger.order_id}}"}}]
WEBHOOK_TRIGGER = {"type": "webhook"}


def enable_webhook(ws, workflow_id, **body):
    client, headers, base = ws
    return client.post(f"{base}/workflows/{workflow_id}/webhook", json=body or None, headers=headers).json()


def hook_path(webhook):
    return "/hooks/" + webhook["url"].rsplit("/", 1)[1]


def test_signed_webhook_starts_workflow(ws):
    client, _, _ = ws
    workflow = create_workflow(ws, WEBHOOK_STEPS, WEBHOOK_TRIGGER)
    webhook = enable_webhook(ws, workflow["id"])
    body = json.dumps({"order_id": 1001}).encode()

    response = client.post(hook_path(webhook), content=body, headers=webhooks.sign(webhook["secret"], body))

    assert response.status_code == 202
    assert response.json()["status"] == "succeeded"


def test_webhook_rejects_bad_or_stale_signatures(ws):
    client, _, _ = ws
    workflow = create_workflow(ws, WEBHOOK_STEPS, WEBHOOK_TRIGGER)
    webhook = enable_webhook(ws, workflow["id"])
    body = b'{"order_id": 1}'

    wrong_secret = webhooks.sign("not-the-secret", body)
    stale = webhooks.sign(webhook["secret"], body, timestamp=time.time() - 3600)
    tampered = webhooks.sign(webhook["secret"], body)

    assert client.post(hook_path(webhook), content=body, headers=wrong_secret).status_code == 401
    assert client.post(hook_path(webhook), content=body, headers=stale).status_code == 401
    assert client.post(hook_path(webhook), content=b'{"order_id": 2}', headers=tampered).status_code == 401
    assert client.post(hook_path(webhook), content=body).status_code == 401
    assert client.post("/hooks/unknown", content=body).status_code == 404


def test_duplicate_delivery_starts_one_execution(ws):
    client, headers, base = ws
    workflow = create_workflow(ws, WEBHOOK_STEPS, WEBHOOK_TRIGGER)
    webhook = enable_webhook(ws, workflow["id"])
    body = b'{"order_id": 7}'

    first = client.post(hook_path(webhook), content=body,
                        headers={**webhooks.sign(webhook["secret"], body), "Idempotency-Key": "delivery-7"})
    second = client.post(hook_path(webhook), content=body,
                         headers={**webhooks.sign(webhook["secret"], body), "Idempotency-Key": "delivery-7"})

    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert first.json()["execution_id"] == second.json()["execution_id"]
    assert len(client.get(f"{base}/executions", headers=headers).json()) == 1


def test_shopify_signed_webhook(ws):
    client, _, _ = ws
    workflow = create_workflow(ws, WEBHOOK_STEPS, WEBHOOK_TRIGGER)
    secret = "shopify-app-secret-0123456789"
    webhook = enable_webhook(ws, workflow["id"], signature_scheme="shopify", secret=secret)
    body = b'{"order_id": 42}'
    signature = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()

    ok = client.post(hook_path(webhook), content=body,
                     headers={"X-Shopify-Hmac-Sha256": signature, "X-Shopify-Webhook-Id": "w-1"})
    bad = client.post(hook_path(webhook), content=body, headers={"X-Shopify-Hmac-Sha256": "AAAA"})

    assert ok.status_code == 202
    assert bad.status_code == 401


def test_webhook_needs_published_webhook_workflow(ws):
    client, _, _ = ws
    draft_only = create_workflow(ws, WEBHOOK_STEPS, WEBHOOK_TRIGGER, publish=False)
    manual = create_workflow(ws, WEBHOOK_STEPS)
    body = b"{}"

    for workflow in (draft_only, manual):
        webhook = enable_webhook(ws, workflow["id"])
        response = client.post(hook_path(webhook), content=body, headers=webhooks.sign(webhook["secret"], body))
        assert response.status_code == 409


def test_webhook_secret_is_not_shown_again(ws):
    client, headers, base = ws
    workflow = create_workflow(ws, WEBHOOK_STEPS, WEBHOOK_TRIGGER)
    webhook = enable_webhook(ws, workflow["id"])

    shown = client.get(f"{base}/workflows/{workflow['id']}/webhook", headers=headers).json()

    assert "secret" not in shown
    assert shown["url"] == webhook["url"]
