import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import update

from autoflow.engine.definition import WorkflowDefinition
from autoflow.engine.templates import TEMPLATES
from autoflow.engine.templates_ecommerce import SAMPLE_SHOPIFY_ORDER
from autoflow.storage.db import session_scope
from autoflow.storage.models import Workspace

NEW = [
    "shipping-notification", "refund-void-invoice", "weekly-sales-summary", "low-stock-alert",
    "order-lines-to-sheet", "vip-thank-you", "support-inbox-assistant", "woocommerce-packing-note",
]
AI_REPLY = {"category": "return or exchange", "confidence": 0.9, "summary": "Mug: 2 left",
            "subject": "Re: Wrong size", "body": "Happy to help.", "injection_suspected": False}


@pytest.fixture(autouse=True)
def fakes():
    with patch("autoflow.engine.executor.sleep"), \
            patch("autoflow.ai.steps.providers.complete", side_effect=lambda s, p: (json.dumps(AI_REPLY), "fake")):
        yield


@pytest.fixture
def ws(client, signup):
    headers, workspace_id = signup()
    with session_scope() as session:
        session.execute(update(Workspace).where(Workspace.id == workspace_id)
                        .values(feature_flags={"smarter_logic": True}))
    base = f"/workspaces/{workspace_id}"
    client.post(f"{base}/connections", json={
        "provider": "smtp", "name": "mailbox",
        "config": {"host": "smtp.example.com", "username": "me@shop.example", "from_address": "me@shop.example"},
        "secrets": {"password": "app-password-1234"},
    }, headers=headers)
    return client, headers, base


def install(ws, slug):
    client, headers, base = ws
    response = client.post(f"{base}/workflows/from-template", json={"template": slug}, headers=headers)
    assert response.status_code == 201, response.text
    workflow = response.json()
    client.post(f"{base}/workflows/{workflow['id']}/publish", headers=headers)
    return workflow


def run(ws, workflow, mode="test", payload=None):
    client, headers, base = ws
    body = {"mode": mode, **({"payload": payload} if payload is not None else {})}
    return client.post(f"{base}/workflows/{workflow['id']}/executions", json=body, headers=headers).json()


def test_the_library_has_the_new_templates_and_all_are_valid(client):
    listed = {t["slug"]: t for t in client.get("/templates").json()}
    assert len(listed) >= 14
    for slug in NEW:
        assert listed[slug]["requires"] and listed[slug]["category"] == "E-commerce"
        WorkflowDefinition.model_validate(TEMPLATES[slug]["definition"])
    assert {"low-stock-alert", "order-lines-to-sheet", "vip-thank-you"} <= {
        slug for slug, t in listed.items() if t["feature"]}


@pytest.mark.parametrize("slug", NEW)
def test_every_new_template_test_runs_with_its_sample_data(ws, slug):
    client, headers, base = ws
    # Templates that read from the shop's own API need its connection (listed in "requires")
    client.post(f"{base}/connections", json={
        "provider": "http", "name": "shop-api",
        "config": {"header_name": "X-Api-Key", "base_url": "https://api.shop.example"},
        "secrets": {"header_value": "key-abcdef-123456"},
    }, headers=headers)
    reply = MagicMock(status_code=200, ok=True, headers={"Content-Type": "application/json"})
    reply.json.return_value = {"products": [{"title": "Mug", "stock": 2}]}
    with patch("autoflow.integrations.actions.check_public_url"),             patch("autoflow.integrations.actions.requests.request", return_value=reply):
        tested = run(ws, install(ws, slug))
    assert tested["status"] == "succeeded", (slug, tested["error"], [s["error"] for s in tested["steps"]])


def test_smart_templates_need_the_feature(client, signup):
    headers, workspace_id = signup(email="plain@example.com")
    refused = client.post(f"/workspaces/{workspace_id}/workflows/from-template",
                          json={"template": "order-lines-to-sheet"}, headers=headers)
    assert refused.status_code == 403
    assert client.post(f"/workspaces/{workspace_id}/workflows/from-template",
                       json={"template": "shipping-notification"}, headers=headers).status_code == 201


def test_line_items_become_one_row_each(ws):
    tested = run(ws, install(ws, "order-lines-to-sheet"))
    rows = tested["steps"][0]["input"]["items"]
    assert [row["values"] for row in rows] == [
        ["#1001", "Ceramic mug", 2, "12.00"], ["#1001", "Coffee beans 250 g", 1, "16.00"]]


def test_big_order_thank_you_only_for_big_orders(ws):
    workflow = install(ws, "vip-thank-you")
    small = run(ws, workflow, payload=SAMPLE_SHOPIFY_ORDER)
    big = run(ws, workflow, payload={**SAMPLE_SHOPIFY_ORDER, "total_price": "1,250.00"})
    assert small["steps"][0]["status"] == "skipped"
    assert big["steps"][0]["status"] == "succeeded"


def test_refund_voids_once_and_emails_once(ws):
    client, headers, base = ws
    invoice_flow = install(ws, "shopify-order-to-invoice")
    run(ws, invoice_flow, mode="live", payload=SAMPLE_SHOPIFY_ORDER)
    refund = install(ws, "refund-void-invoice")

    first = run(ws, refund, mode="live", payload={"order_id": SAMPLE_SHOPIFY_ORDER["id"], "note": "Damaged"})
    assert first["status"] == "waiting_approval"
    again = run(ws, refund, mode="live", payload={"order_id": SAMPLE_SHOPIFY_ORDER["id"], "note": "Damaged"})
    assert again["status"] == "succeeded"
    assert {s["step_id"]: s["status"] for s in again["steps"]}["send"] == "skipped"

    invoice = client.get(f"{base}/invoices", headers=headers).json()[0]
    assert invoice["void_reason"] == "Refunded: Damaged"


def test_shipping_email_skipped_without_tracking(ws):
    workflow = install(ws, "shipping-notification")
    done = run(ws, workflow, payload={"order_id": 1, "email": "a@example.com", "name": "#9"})
    assert done["steps"][0]["status"] == "skipped"
