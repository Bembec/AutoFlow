import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import update

from luphina.engine.templates_ecommerce import SAMPLE_SHOPIFY_ORDER
from luphina.engine.templates_ecommerce_four import SAMPLE_BIG_REFUND, SAMPLE_RISKY_ORDER
from luphina.storage.db import session_scope
from luphina.storage.models import Workspace

NEW = [
    "shopify-cancelled-void", "daily-order-digest", "big-refund-alert", "high-value-first-order-check",
    "foreign-review-reply", "loyal-customer-thanks", "abandoned-checkouts-to-airtable", "support-log-to-sheet",
]
AI_REPLY = {"category": "delivery question", "summary": "3 orders, 112 EUR.", "translation": "Very nice mug, a bit late.",
            "subject": "Gracias", "body": "¡Gracias por tu reseña!", "confidence": 0.9, "injection_suspected": False}


@pytest.fixture(autouse=True)
def fakes():
    reply = MagicMock(status_code=200, ok=True, headers={"Content-Type": "application/json"})
    reply.json.return_value = {"orders": [{"name": "#1001", "total": "47.60"}]}
    with patch("luphina.engine.executor.sleep"), \
            patch("luphina.ai.steps.providers.complete", side_effect=lambda s, p: (json.dumps(AI_REPLY), "fake")), \
            patch("luphina.integrations.actions.check_public_url"), \
            patch("luphina.integrations.actions.requests.request", return_value=reply):
        yield


@pytest.fixture
def ws(client, signup):
    headers, workspace_id = signup()
    with session_scope() as session:
        session.execute(update(Workspace).where(Workspace.id == workspace_id)
                        .values(feature_flags={"smarter_logic": True}))
    base = f"/workspaces/{workspace_id}"
    client.post(f"{base}/connections", json={
        "provider": "http", "name": "shop-api",
        "config": {"header_name": "X-Api-Key", "base_url": "https://api.shop.example"},
        "secrets": {"header_value": "key-abcdef-123456"},
    }, headers=headers)
    return client, headers, base


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


def test_library_grows(client):
    assert sum(t["category"] == "E-commerce" for t in client.get("/templates").json()) >= 32


@pytest.mark.parametrize("slug", NEW)
def test_every_new_template_runs_every_step(ws, slug):
    tested = run(ws, install(ws, slug))
    assert tested["status"] == "succeeded", (slug, tested["error"])
    assert "skipped" not in statuses(tested).values(), (slug, statuses(tested))


def test_conditions_skip_the_ordinary_cases(ws):
    refund = install(ws, "big-refund-alert")
    assert statuses(run(ws, refund, {**SAMPLE_BIG_REFUND, "amount": "12.00"}))["send"] == "skipped"

    risky = install(ws, "high-value-first-order-check")
    regular = {**SAMPLE_RISKY_ORDER, "customer": {**SAMPLE_RISKY_ORDER["customer"], "orders_count": 5}}
    assert set(statuses(run(ws, risky, regular)).values()) == {"skipped"}
    assert set(statuses(run(ws, risky, SAMPLE_SHOPIFY_ORDER)).values()) == {"skipped"}  # small first order

    loyal = install(ws, "loyal-customer-thanks")
    second = {**SAMPLE_SHOPIFY_ORDER, "customer": {**SAMPLE_SHOPIFY_ORDER["customer"], "orders_count": 2}}
    assert statuses(run(ws, loyal, second))["send"] == "skipped"
