from unittest.mock import MagicMock, patch

import pytest

from luphina import observability


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("luphina.engine.executor.sleep"):
        yield


@pytest.fixture
def ws(client, signup):
    headers, workspace_id = signup()
    return client, headers, f"/workspaces/{workspace_id}"


def response(status=200, payload=None):
    result = MagicMock()
    result.status_code = status
    result.ok = status < 400
    result.json.return_value = payload or {}
    result.text = str(payload)
    return result


# --- OCR counts toward the daily AI limit -----------------------------------------------

def test_reading_scans_counts_toward_the_ai_limit(ws):
    client, headers, base = ws
    client.patch(f"{base}/policies", json={"max_ai_calls_per_day": 1}, headers=headers)
    workflow = client.post(f"{base}/workflows", json={"name": "D", "definition": {
        "trigger": {"type": "document"},
        "steps": [{"id": "log", "action": "log_activity", "inputs": {"message": "{{trigger.text}}"}}],
    }}, headers=headers).json()

    def upload():
        return client.post(f"{base}/workflows/{workflow['id']}/documents",
                           files={"file": ("photo.png", PNG, "image/png")}, data={"mode": "test"}, headers=headers)

    with patch("luphina.documents.providers.transcribe", return_value=("Receipt 12.00", "fake")) as ocr:
        first = upload()
        second = upload()

    assert first.status_code == 201
    assert second.status_code == 422
    assert "Daily limit of 1 AI calls" in second.json()["detail"]
    assert ocr.call_count == 1
    assert client.get(f"{base}/policies", headers=headers).json()["usage_today"]["ai_calls"] == 1


def test_text_files_do_not_use_ai_quota(ws):
    client, headers, base = ws
    client.patch(f"{base}/policies", json={"max_ai_calls_per_day": 0}, headers=headers)
    workflow = client.post(f"{base}/workflows", json={"name": "D", "definition": {
        "trigger": {"type": "document"},
        "steps": [{"id": "log", "action": "log_activity", "inputs": {"message": "{{trigger.text}}"}}],
    }}, headers=headers).json()

    result = client.post(f"{base}/workflows/{workflow['id']}/documents",
                         files={"file": ("a.txt", b"plain text", "text/plain")}, data={"mode": "test"}, headers=headers)

    assert result.status_code == 201


# --- Shopify Admin connector ---------------------------------------------------------------

SHOPIFY = {
    "provider": "shopify", "name": "store",
    "config": {"shop_domain": "mug-and-bean.myshopify.com"},
    "secrets": {"access_token": "shpat_secret_token_123"},
}


@pytest.mark.parametrize("domain", ["evil.example.com", "mug.myshopify.com.evil.com", "https://mug.myshopify.com"])
def test_shopify_domain_must_be_a_myshopify_address(ws, domain):
    client, headers, base = ws

    result = client.post(f"{base}/connections", json={**SHOPIFY, "config": {"shop_domain": domain}}, headers=headers)

    assert result.status_code == 409
    assert "myshopify.com" in result.json()["detail"]


def tag_workflow(ws):
    client, headers, base = ws
    client.post(f"{base}/connections", json=SHOPIFY, headers=headers)
    workflow = client.post(f"{base}/workflows", json={"name": "Tag", "definition": {
        "trigger": {"type": "webhook"},
        "steps": [{"id": "tag", "action": "shopify_tag_order",
                   "inputs": {"connection": "store", "order_id": "{{trigger.id}}", "tags": "invoiced, vip"}}],
    }}, headers=headers).json()
    client.post(f"{base}/workflows/{workflow['id']}/publish", headers=headers)
    return workflow


def run_live(ws, workflow_id, payload):
    client, headers, base = ws
    return client.post(f"{base}/workflows/{workflow_id}/executions",
                       json={"mode": "live", "payload": payload}, headers=headers).json()


def test_shopify_tags_are_merged_not_replaced(ws):
    workflow = tag_workflow(ws)

    with patch("luphina.integrations.actions.requests") as http:
        http.get.return_value = response(200, {"order": {"id": 42, "tags": "wholesale, vip"}})
        http.put.return_value = response(200, {"order": {"id": 42}})
        run = run_live(ws, workflow["id"], {"id": 42})

    assert run["status"] == "succeeded"
    url = http.put.call_args.args[0]
    assert url.startswith("https://mug-and-bean.myshopify.com/admin/api/")
    assert url.endswith("/orders/42.json")
    assert http.put.call_args.kwargs["json"] == {"order": {"id": 42, "tags": "wholesale, vip, invoiced"}}
    assert http.put.call_args.kwargs["headers"]["X-Shopify-Access-Token"] == "shpat_secret_token_123"


def test_shopify_tagging_twice_changes_nothing(ws):
    workflow = tag_workflow(ws)

    with patch("luphina.integrations.actions.requests") as http:
        http.get.return_value = response(200, {"order": {"id": 42, "tags": "invoiced, vip"}})
        run = run_live(ws, workflow["id"], {"id": 42})

    assert run["steps"][0]["output"] == {"tags": "invoiced, vip", "changed": False}
    http.put.assert_not_called()


def test_shopify_rejects_non_numeric_order_ids(ws):
    workflow = tag_workflow(ws)

    with patch("luphina.integrations.actions.requests") as http:
        run = run_live(ws, workflow["id"], {"id": "42/../../shop"})

    assert run["status"] == "failed"
    assert "numeric" in run["error"]
    http.get.assert_not_called()


def test_shopify_note_action(ws):
    client, headers, base = ws
    client.post(f"{base}/connections", json=SHOPIFY, headers=headers)
    workflow = client.post(f"{base}/workflows", json={"name": "Note", "definition": {
        "steps": [{"id": "note", "action": "shopify_set_order_note",
                   "inputs": {"connection": "store", "order_id": 7, "note": "Invoice INV-00007 sent"}}],
    }}, headers=headers).json()
    client.post(f"{base}/workflows/{workflow['id']}/publish", headers=headers)

    with patch("luphina.integrations.actions.requests") as http:
        http.put.return_value = response(200, {})
        run = run_live(ws, workflow["id"], {})

    assert run["status"] == "succeeded"
    assert http.put.call_args.kwargs["json"] == {"order": {"id": 7, "note": "Invoice INV-00007 sent"}}


# --- error tracking -------------------------------------------------------------------------

def test_error_tracking_is_off_without_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)

    assert observability.init_error_tracking("api") is False


def test_error_tracking_starts_without_personal_data(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "https://key@sentry.example/1")
    fake = MagicMock()

    with patch.dict("sys.modules", {"sentry_sdk": fake}):
        assert observability.init_error_tracking("worker") is True

    assert fake.init.call_args.kwargs["send_default_pii"] is False
    fake.set_tag.assert_called_once_with("component", "worker")
