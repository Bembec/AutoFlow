import base64
import copy
import hashlib
import hmac
import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import update

from autoflow.commerce.orders import OrderError, parse_order
from autoflow.engine import queue
from autoflow.engine.templates_ecommerce import SAMPLE_REVIEW, SAMPLE_SHOPIFY_CHECKOUT, SAMPLE_SHOPIFY_ORDER
from autoflow.storage.db import engine as db_engine
from autoflow.storage.db import session_scope, utc_now
from autoflow.storage.models import StepExecution, WorkflowExecution


SHOPIFY_SECRET = "shopify-app-secret-0123456789"


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("autoflow.engine.executor.sleep"):
        yield


@pytest.fixture
def ws(client, signup):
    headers, workspace_id = signup()
    client.post(f"/workspaces/{workspace_id}/connections", json={
        "provider": "smtp", "name": "mailbox",
        "config": {"host": "smtp.example.com", "username": "shop@example.com", "from_address": "shop@example.com"},
        "secrets": {"password": "app-password-123"},
    }, headers=headers)
    return client, headers, f"/workspaces/{workspace_id}"


def install(ws, slug, publish=True):
    client, headers, base = ws
    workflow = client.post(f"{base}/workflows/from-template", json={"template": slug}, headers=headers).json()
    if publish:
        client.post(f"{base}/workflows/{workflow['id']}/publish", headers=headers)
    return workflow


def shopify_hook(ws, workflow_id):
    client, headers, base = ws
    hook = client.post(
        f"{base}/workflows/{workflow_id}/webhook",
        json={"signature_scheme": "shopify", "secret": SHOPIFY_SECRET},
        headers=headers,
    ).json()

    def deliver(payload, delivery_id):
        body = json.dumps(payload).encode()
        signature = base64.b64encode(hmac.new(SHOPIFY_SECRET.encode(), body, hashlib.sha256).digest()).decode()
        return client.post(
            "/hooks/" + hook["url"].rsplit("/", 1)[1],
            content=body,
            headers={"X-Shopify-Hmac-Sha256": signature, "X-Shopify-Webhook-Id": delivery_id},
        )

    return deliver


def execution(ws, execution_id):
    client, headers, base = ws
    return client.get(f"{base}/executions/{execution_id}", headers=headers).json()


def steps(execution_data):
    return {s["step_id"]: s for s in execution_data["steps"]}


# --- order parsing ----------------------------------------------------------------

def test_parse_shopify_order():
    order = parse_order(SAMPLE_SHOPIFY_ORDER)

    assert order.external_ref == "820982911946154508"
    assert order.customer_name == "Ada Lovelace"
    assert order.customer_email == "ada@example.com"
    assert (order.subtotal, order.tax, order.total) == (Decimal("40.00"), Decimal("7.60"), Decimal("47.60"))
    assert order.lines[0] == {"title": "Ceramic mug", "quantity": 2, "unit_price": "12.00", "amount": "24.00"}
    assert order.checkout_token == "chk_8f2c1a"


def test_parse_generic_order():
    order = parse_order({
        "order_id": "A-7", "customer_name": "Bob", "currency": "gbp", "tax": "2",
        "items": [{"title": "Tea", "quantity": 3, "unit_price": "4.50"}],
    })

    assert (order.subtotal, order.total, order.currency) == (Decimal("13.50"), Decimal("15.50"), "GBP")


@pytest.mark.parametrize("data", [None, {"foo": 1}, {"items": []}, {"line_items": [{"price": "x"}], "id": 1}])
def test_bad_orders_are_rejected(data):
    with pytest.raises(OrderError):
        parse_order(data)


# --- templates ----------------------------------------------------------------------

def test_templates_list_ecommerce_pack(client):
    templates = {t["slug"]: t for t in client.get("/templates").json()}

    for slug in ("shopify-order-to-invoice", "abandoned-cart-follow-up", "review-reply-assistant"):
        assert templates[slug]["category"] == "E-commerce"
        assert templates[slug]["requires"]


def test_order_template_test_run_is_harmless(ws):
    client, headers, base = ws
    workflow = install(ws, "shopify-order-to-invoice", publish=False)

    run = client.post(f"{base}/workflows/{workflow['id']}/executions", json={"mode": "test"}, headers=headers).json()

    assert run["status"] == "succeeded"
    assert steps(run)["invoice"]["output"]["total"] == "47.60"
    assert steps(run)["send"]["output"]["dry_run"] is True
    assert client.get(f"{base}/invoices", headers=headers).json() == []


# --- order → invoice, live ---------------------------------------------------------

def test_shopify_order_creates_one_invoice_and_waits_to_email(ws):
    client, headers, base = ws
    client.patch(f"{base}/business", json={
        "business_name": "Mug & Bean Ltd", "business_address": "1 High St\nLondon", "tax_id": "GB123", "invoice_prefix": "MB-",
    }, headers=headers)
    workflow = install(ws, "shopify-order-to-invoice")
    deliver = shopify_hook(ws, workflow["id"])

    first = deliver(SAMPLE_SHOPIFY_ORDER, "delivery-1").json()
    run = execution(ws, first["execution_id"])

    assert run["status"] == "waiting_approval"
    invoice = steps(run)["invoice"]["output"]
    assert invoice["invoice_number"] == "MB-00001"
    assert invoice["created"] is True
    assert steps(run)["track"]["output"] == {"recorded": True}

    approval = client.get(f"{base}/approvals", params={"kind": "step", "status": "pending"}, headers=headers).json()[0]
    assert approval["payload"]["inputs"]["subject"] == "Your invoice MB-00001 for order #1001"
    assert invoice["url"] in approval["payload"]["inputs"]["body"]

    # Shopify may send the same order again under a new delivery id
    again = deliver(SAMPLE_SHOPIFY_ORDER, "delivery-2").json()
    assert steps(execution(ws, again["execution_id"]))["invoice"]["output"]["invoice_number"] == "MB-00001"

    second_order = {**SAMPLE_SHOPIFY_ORDER, "id": 999, "name": "#1002"}
    third = deliver(second_order, "delivery-3").json()
    assert steps(execution(ws, third["execution_id"]))["invoice"]["output"]["invoice_number"] == "MB-00002"

    listed = client.get(f"{base}/invoices", headers=headers).json()
    assert [i["number"] for i in listed] == ["MB-00002", "MB-00001"]


def test_public_invoice_page_escapes_content(ws):
    client, headers, base = ws
    workflow = install(ws, "shopify-order-to-invoice")
    deliver = shopify_hook(ws, workflow["id"])
    hostile = copy.deepcopy(SAMPLE_SHOPIFY_ORDER)
    hostile["line_items"][0]["title"] = "<script>alert(1)</script>"

    run = execution(ws, deliver(hostile, "d-1").json()["execution_id"])
    url = steps(run)["invoice"]["output"]["url"]
    page = client.get("/invoices/" + url.rsplit("/", 1)[1])

    assert page.status_code == 200
    assert "<script>alert(1)</script>" not in page.text
    assert "&lt;script&gt;" in page.text
    assert "47.60" in page.text
    assert page.headers["X-Robots-Tag"] == "noindex"
    assert client.get("/invoices/not-a-real-token").status_code == 404


def test_invoices_are_private_to_their_workspace(ws, signup):
    client, headers, base = ws
    workflow = install(ws, "shopify-order-to-invoice")
    shopify_hook(ws, workflow["id"])(SAMPLE_SHOPIFY_ORDER, "d-1")
    other_headers, other_workspace = signup("other@example.com")

    assert client.get(f"{base}/invoices", headers=other_headers).status_code == 404
    assert client.get(f"/workspaces/{other_workspace}/invoices", headers=other_headers).json() == []


# --- abandoned cart ------------------------------------------------------------------

def finish_delay(execution_id):
    past = utc_now() - timedelta(minutes=1)
    with db_engine.begin() as connection:
        connection.execute(update(WorkflowExecution).where(WorkflowExecution.id == execution_id).values(run_after=past))
        connection.execute(
            update(StepExecution)
            .where(StepExecution.execution_id == execution_id, StepExecution.action == "delay")
            .values(output={"resume_at": past.isoformat()})
        )
    with session_scope() as session:
        queue.run_due(session, "test-worker")


def start_cart(ws, cart):
    workflow = install(ws, "abandoned-cart-follow-up")
    run = shopify_hook(ws, workflow["id"])(cart, f"cart-{cart['token']}").json()
    assert execution(ws, run["execution_id"])["status"] == "queued"  # waiting an hour
    finish_delay(run["execution_id"])
    return execution(ws, run["execution_id"])


def test_cart_reminder_is_never_sent_without_order_tracking(ws):
    run = start_cart(ws, SAMPLE_SHOPIFY_CHECKOUT)

    assert run["status"] == "succeeded"
    assert steps(run)["status"]["output"] == {"completed": None, "tracking_active": False}
    assert steps(run)["remind"]["status"] == "skipped"


def test_cart_reminder_for_unfinished_checkout(ws):
    orders = install(ws, "shopify-order-to-invoice")
    shopify_hook(ws, orders["id"])(SAMPLE_SHOPIFY_ORDER, "order-1")  # tracking now active

    run = start_cart(ws, SAMPLE_SHOPIFY_CHECKOUT)

    assert steps(run)["status"]["output"]["completed"] is False
    assert run["status"] == "waiting_approval"
    assert steps(run)["remind"]["input"]["to"] == "grace@example.com"
    assert "recover" in steps(run)["remind"]["input"]["body"]


def test_no_cart_reminder_for_buyers(ws):
    orders = install(ws, "shopify-order-to-invoice")
    bought = {**SAMPLE_SHOPIFY_ORDER, "checkout_token": SAMPLE_SHOPIFY_CHECKOUT["token"]}
    shopify_hook(ws, orders["id"])(bought, "order-1")

    run = start_cart(ws, SAMPLE_SHOPIFY_CHECKOUT)

    assert steps(run)["status"]["output"]["completed"] is True
    assert steps(run)["remind"]["status"] == "skipped"
    assert run["status"] == "succeeded"


# --- review replies -----------------------------------------------------------------

def test_review_reply_drafts_and_waits_for_approval(ws):
    client, headers, base = ws
    workflow = install(ws, "review-reply-assistant")
    replies = iter([
        {"category": "disappointed", "reason": "late delivery", "confidence": 0.9},
        {"subject": "Sorry about the wait", "body": "Hi Alan, we are sorry...", "confidence": 0.9},
    ])

    with patch("autoflow.ai.steps.providers.complete", side_effect=lambda s, p: (json.dumps(next(replies)), "fake")):
        run = client.post(
            f"{base}/workflows/{workflow['id']}/executions",
            json={"mode": "live", "payload": SAMPLE_REVIEW},
            headers=headers,
        ).json()

    assert run["status"] == "waiting_approval"
    assert steps(run)["mood"]["output"]["category"] == "disappointed"
    send = steps(run)["send"]["input"]
    assert (send["to"], send["subject"]) == ("alan@example.com", "Sorry about the wait")
