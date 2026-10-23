import json
from unittest.mock import patch

import pytest
from sqlalchemy import update

from autoflow.engine.templates_ecommerce import SAMPLE_REVIEW, SAMPLE_SHOPIFY_ORDER, SAMPLE_WOOCOMMERCE_ORDER
from autoflow.storage.db import session_scope
from autoflow.storage.models import Workspace

NEW = [
    "first-order-welcome", "review-request-later", "orders-to-sheet", "woocommerce-orders-to-sheet",
    "customers-to-airtable", "tag-big-orders", "low-rating-alert", "payment-failed-reminder",
    "woocommerce-completed-thanks", "woocommerce-cancelled-void", "wholesale-lead-alert",
]
AI_REPLY = {"category": "wholesale or bulk enquiry", "confidence": 0.9, "summary": "12 cafes want 400 mugs",
            "injection_suspected": False}


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
    return client, headers, f"/workspaces/{workspace_id}"


def install(ws, slug):
    client, headers, base = ws
    created = client.post(f"{base}/workflows/from-template", json={"template": slug}, headers=headers)
    assert created.status_code == 201, created.text
    return created.json()


def run(ws, workflow, payload=None):
    client, headers, base = ws
    body = {"mode": "test", **({"payload": payload} if payload is not None else {})}
    return client.post(f"{base}/workflows/{workflow['id']}/executions", json=body, headers=headers).json()


def statuses(execution):
    return {s["step_id"]: s["status"] for s in execution["steps"]}


def test_the_library_reaches_25(client):
    assert len(client.get("/templates").json()) >= 25


@pytest.mark.parametrize("slug", NEW)
def test_every_template_test_runs_with_its_sample_data(ws, slug):
    tested = run(ws, install(ws, slug))
    assert tested["status"] == "succeeded", (slug, tested["error"])
    # The sample data is chosen so every step really runs
    assert "skipped" not in statuses(tested).values(), (slug, statuses(tested))


def test_conditions_skip_the_cases_they_should(ws):
    welcome = install(ws, "first-order-welcome")
    returning = {**SAMPLE_SHOPIFY_ORDER, "customer": {**SAMPLE_SHOPIFY_ORDER["customer"], "orders_count": 4}}
    assert statuses(run(ws, welcome, returning))["send"] == "skipped"

    tag = install(ws, "tag-big-orders")
    assert statuses(run(ws, tag, SAMPLE_SHOPIFY_ORDER))["tag"] == "skipped"  # 47.60 is not over 150

    alert = install(ws, "low-rating-alert")
    assert statuses(run(ws, alert, {**SAMPLE_REVIEW, "rating": 5}))["send"] == "skipped"

    cancelled = install(ws, "woocommerce-cancelled-void")
    assert statuses(run(ws, cancelled, {**SAMPLE_WOOCOMMERCE_ORDER, "status": "refunded"}))["void"] == "succeeded"
    assert statuses(run(ws, cancelled, SAMPLE_WOOCOMMERCE_ORDER))["void"] == "skipped"  # still processing


def test_wholesale_alert_ignores_normal_customers(ws):
    AI_REPLY["category"] = "normal customer"
    try:
        done = run(ws, install(ws, "wholesale-lead-alert"))
    finally:
        AI_REPLY["category"] = "wholesale or bulk enquiry"
    assert statuses(done) == {"kind": "succeeded", "summary": "skipped", "send": "skipped"}
