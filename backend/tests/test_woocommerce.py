import base64
import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from autoflow.commerce.orders import parse_order
from autoflow.engine.templates_ecommerce import SAMPLE_SHOPIFY_ORDER, SAMPLE_WOOCOMMERCE_ORDER


SECRET = "woo-webhook-secret-0123456789"


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("autoflow.engine.executor.sleep"):
        yield


@pytest.fixture
def ws(client, signup):
    headers, workspace_id = signup()
    base = f"/workspaces/{workspace_id}"
    client.post(f"{base}/connections", json={
        "provider": "smtp", "name": "mailbox",
        "config": {"host": "smtp.example.com", "username": "shop@example.com", "from_address": "shop@example.com"},
        "secrets": {"password": "app-password-123"},
    }, headers=headers)
    return client, headers, base


def woo_hook(ws, workflow_id):
    client, headers, base = ws
    hook = client.post(f"{base}/workflows/{workflow_id}/webhook",
                       json={"signature_scheme": "woocommerce", "secret": SECRET}, headers=headers).json()
    path = "/hooks/" + hook["url"].rsplit("/", 1)[1]

    def deliver(body, delivery_id="d-1", signed=True):
        raw = body if isinstance(body, bytes) else json.dumps(body).encode()
        signature = base64.b64encode(hmac.new(SECRET.encode(), raw, hashlib.sha256).digest()).decode()
        headers_ = {"X-WC-Webhook-Delivery-ID": delivery_id}
        if signed:
            headers_["X-WC-Webhook-Signature"] = signature
        return client.post(path, content=raw, headers=headers_)

    return deliver


def install(ws, slug):
    client, headers, base = ws
    workflow = client.post(f"{base}/workflows/from-template", json={"template": slug}, headers=headers).json()
    client.post(f"{base}/workflows/{workflow['id']}/publish", headers=headers)
    return workflow


def execution(ws, execution_id):
    client, headers, base = ws
    run = client.get(f"{base}/executions/{execution_id}", headers=headers).json()
    return run, {s["step_id"]: s for s in run["steps"]}


def test_parse_woocommerce_order():
    order = parse_order(SAMPLE_WOOCOMMERCE_ORDER)

    assert order.external_ref == "727"
    assert order.customer_name == "Ada Lovelace"
    assert order.customer_email == "ada@example.com"
    assert (order.subtotal, order.tax, order.total) == (Decimal("40.00"), Decimal("7.60"), Decimal("47.60"))
    assert order.lines[0] == {"title": "Ceramic mug", "quantity": 2, "unit_price": "12.00", "amount": "24.00"}
    assert order.checkout_token == "b1f4c9e2"
    # Shopify orders are still recognised as Shopify
    assert parse_order(SAMPLE_SHOPIFY_ORDER).customer_name == "Ada Lovelace"


def test_woocommerce_ping_is_answered_without_a_run(ws):
    client, headers, base = ws
    workflow = install(ws, "woocommerce-order-to-invoice")

    response = woo_hook(ws, workflow["id"])(b"webhook_id=15", signed=False)

    assert response.status_code == 200
    assert response.json() == {"ping": True}
    assert client.get(f"{base}/executions", headers=headers).json() == []


def test_woocommerce_signature_is_required(ws):
    workflow = install(ws, "woocommerce-order-to-invoice")
    deliver = woo_hook(ws, workflow["id"])

    assert deliver(SAMPLE_WOOCOMMERCE_ORDER, signed=False).status_code == 401
    assert deliver(SAMPLE_WOOCOMMERCE_ORDER).status_code == 202


def test_order_updates_create_one_invoice_and_one_email(ws):
    client, headers, base = ws
    workflow = install(ws, "woocommerce-order-to-invoice")
    deliver = woo_hook(ws, workflow["id"])

    first, steps = execution(ws, deliver(SAMPLE_WOOCOMMERCE_ORDER, "d-1").json()["execution_id"])
    assert first["status"] == "waiting_approval"
    assert steps["invoice"]["output"]["invoice_number"] == "INV-00001"
    assert steps["send"]["input"]["subject"] == "Your invoice INV-00001 for order 727"

    # WooCommerce sends "order updated" again later: same invoice, no second email
    updated = {**SAMPLE_WOOCOMMERCE_ORDER, "status": "completed"}
    second, steps = execution(ws, deliver(updated, "d-2").json()["execution_id"])
    assert second["status"] == "succeeded"
    assert steps["invoice"]["output"]["created"] is False
    assert steps["send"]["status"] == "skipped"

    pending = client.get(f"{base}/approvals", params={"status": "pending"}, headers=headers).json()
    assert len(pending) == 1


def test_unpaid_orders_get_no_invoice(ws):
    workflow = install(ws, "woocommerce-order-to-invoice")

    run, steps = execution(ws, woo_hook(ws, workflow["id"])({**SAMPLE_WOOCOMMERCE_ORDER, "status": "pending"}).json()["execution_id"])

    assert steps["invoice"]["status"] == "skipped"
    assert steps["send"]["status"] == "skipped"
    assert run["status"] == "succeeded"


def test_shopify_repeat_sends_no_second_email(ws):
    from test_ecommerce import SHOPIFY_SECRET  # noqa: F401  (same fixture data style)

    client, headers, base = ws
    workflow = install(ws, "shopify-order-to-invoice")
    hook = client.post(f"{base}/workflows/{workflow['id']}/webhook",
                       json={"signature_scheme": "shopify", "secret": SECRET}, headers=headers).json()
    raw = json.dumps(SAMPLE_SHOPIFY_ORDER).encode()
    signature = base64.b64encode(hmac.new(SECRET.encode(), raw, hashlib.sha256).digest()).decode()
    path = "/hooks/" + hook["url"].rsplit("/", 1)[1]

    for delivery in ("a", "b"):
        client.post(path, content=raw, headers={"X-Shopify-Hmac-Sha256": signature, "X-Shopify-Webhook-Id": delivery})

    assert len(client.get(f"{base}/approvals", params={"status": "pending"}, headers=headers).json()) == 1


# --- WooCommerce REST connector -------------------------------------------------------

WOO = {
    "provider": "woocommerce", "name": "store",
    "config": {"store_url": "https://shop.example"},
    "secrets": {"consumer_key": "ck_123", "consumer_secret": "cs_456"},
}


def ok(payload):
    response = MagicMock(status_code=200, ok=True)
    response.json.return_value = payload
    return response


def test_store_url_must_use_https(ws):
    client, headers, base = ws

    response = client.post(f"{base}/connections", json={**WOO, "config": {"store_url": "http://shop.example"}}, headers=headers)

    assert response.status_code == 409


def run_steps(ws, steps):
    client, headers, base = ws
    client.post(f"{base}/connections", json=WOO, headers=headers)
    workflow = client.post(f"{base}/workflows", json={"name": "W", "definition": {"steps": steps}}, headers=headers).json()
    client.post(f"{base}/workflows/{workflow['id']}/publish", headers=headers)
    return client.post(f"{base}/workflows/{workflow['id']}/executions", json={"mode": "live"}, headers=headers).json()


def test_add_order_note(ws):
    with (
        patch("autoflow.integrations.actions.check_public_url"),
        patch("autoflow.integrations.actions.requests") as http,
    ):
        http.post.return_value = ok({"id": 99})
        run = run_steps(ws, [{"id": "note", "action": "woocommerce_add_order_note",
                              "inputs": {"connection": "store", "order_id": 727, "note": "Invoice sent"}}])

    assert run["status"] == "succeeded"
    assert http.post.call_args.args[0] == "https://shop.example/wp-json/wc/v3/orders/727/notes"
    assert http.post.call_args.kwargs["auth"] == ("ck_123", "cs_456")
    assert http.post.call_args.kwargs["json"] == {"note": "Invoice sent", "customer_note": False}


def test_status_change_needs_approval_and_a_valid_status(ws):
    run = run_steps(ws, [{"id": "status", "action": "woocommerce_set_order_status",
                          "inputs": {"connection": "store", "order_id": 727, "status": "refunded"}}])
    assert run["status"] == "waiting_approval"

    client, headers, base = ws
    approval = client.get(f"{base}/approvals", params={"kind": "step"}, headers=headers).json()[0]
    with patch("autoflow.integrations.actions.requests") as http:
        client.post(f"{base}/approvals/{approval['id']}/approve", headers=headers)

    done, _ = execution(ws, run["id"])
    assert done["status"] == "failed"
    assert "status must be one of" in done["error"]
    http.put.assert_not_called()
