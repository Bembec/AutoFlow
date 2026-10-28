import hashlib
import hmac
import json
import time
from unittest.mock import patch

import pytest

from luphina.billing import plans, stripe


@pytest.fixture(autouse=True)
def fakes():
    with (
        patch("luphina.engine.executor.sleep"),
        patch("luphina.engine.actions.fetch_eur_to_usd", return_value=(1.1, "2026-10-21")) as rate,
    ):
        yield rate


@pytest.fixture
def small_plans(monkeypatch, tmp_path):
    """A free plan with 2 included tasks, to test caps quickly."""

    custom = json.loads(plans.DEFAULT_PLANS_FILE.read_text())
    custom["free"]["included_tasks"] = 2
    path = tmp_path / "plans.json"
    path.write_text(json.dumps(custom))
    monkeypatch.setenv("LUPHINA_PLANS_FILE", str(path))
    plans.all_plans.cache_clear()
    yield
    plans.all_plans.cache_clear()


@pytest.fixture
def free_ws(client, signup):
    headers, workspace_id = signup(plan="free")
    return client, headers, f"/workspaces/{workspace_id}", workspace_id


QUOTE_STEPS = [{"id": "quote", "action": "exchange_rate_quote", "inputs": {"amount_eur": 10}}]
LOCAL_STEPS = [{"id": "log", "action": "log_activity", "inputs": {"message": "x"}}]


def create(ws, steps, publish=True):
    client, headers, base, _ = ws
    workflow = client.post(f"{base}/workflows", json={"name": "W", "definition": {"steps": steps}}, headers=headers)
    if workflow.status_code == 201 and publish:
        client.post(f"{base}/workflows/{workflow.json()['id']}/publish", headers=headers)
    return workflow


def run(ws, workflow_id, mode="live"):
    client, headers, base, _ = ws
    return client.post(f"{base}/workflows/{workflow_id}/executions", json={"mode": mode}, headers=headers).json()


def billing(ws):
    client, headers, base, _ = ws
    return client.get(f"{base}/billing", headers=headers).json()


# --- metering -----------------------------------------------------------------

def test_only_successful_live_app_calls_are_billed(free_ws, fakes):
    quote = create(free_ws, QUOTE_STEPS).json()
    local = create(free_ws, LOCAL_STEPS).json()

    run(free_ws, quote["id"])                 # billable: live + calls an app
    run(free_ws, quote["id"], mode="test")    # free: test run
    run(free_ws, local["id"])                 # free: no app or AI call
    fakes.return_value = (None, None)
    run(free_ws, quote["id"])                 # free: failed step

    assert billing(free_ws)["usage"]["billable_tasks"] == 1


def test_rules_only_classification_is_not_billed(free_ws):
    workflow = create(free_ws, [
        {"id": "classify", "action": "classify_enquiry", "inputs": {"message": "price?"}},
    ]).json()

    run(free_ws, workflow["id"])

    assert billing(free_ws)["usage"]["billable_tasks"] == 0


def test_retry_after_failure_bills_once(free_ws, fakes):
    client, headers, base, _ = free_ws
    workflow = create(free_ws, QUOTE_STEPS + [
        {"id": "quote2", "action": "exchange_rate_quote", "inputs": {"amount_eur": 20}},
    ]).json()

    fakes.side_effect = [(1.1, "d"), (None, None)]
    failed = run(free_ws, workflow["id"])
    assert failed["status"] == "failed"

    fakes.side_effect = None
    fakes.return_value = (1.1, "d")
    retried = client.post(f"{base}/executions/{failed['id']}/retry", headers=headers).json()

    assert retried["status"] == "succeeded"
    # quote (once, not re-run) + quote2 (after retry)
    assert billing(free_ws)["usage"]["billable_tasks"] == 2


def test_hard_cap_stops_billable_steps(small_plans, free_ws):
    workflow = create(free_ws, QUOTE_STEPS).json()

    assert run(free_ws, workflow["id"])["status"] == "succeeded"
    assert run(free_ws, workflow["id"])["status"] == "succeeded"
    capped = run(free_ws, workflow["id"])

    assert capped["status"] == "failed"
    assert "tasks for this period are used up" in capped["error"]
    # Test runs and non-billable workflows still work at the cap
    assert run(free_ws, workflow["id"], mode="test")["status"] == "succeeded"

    summary = billing(free_ws)
    assert summary["usage"] == {"billable_tasks": 2, "included_tasks": 2, "projected_tasks": summary["usage"]["projected_tasks"]}
    assert any("used" in alert for alert in summary["alerts"])


def test_free_plan_always_has_a_hard_cap(free_ws):
    client, headers, base, _ = free_ws

    response = client.patch(f"{base}/billing", json={"hard_cap": False}, headers=headers)

    assert response.status_code == 409


# --- plan limits ----------------------------------------------------------------

def test_free_plan_workflow_limit(free_ws):
    for _ in range(5):
        assert create(free_ws, LOCAL_STEPS, publish=False).status_code == 201

    sixth = create(free_ws, LOCAL_STEPS, publish=False)

    assert sixth.status_code == 409
    assert "allows 5 workflows" in sixth.json()["detail"]
    assert billing(free_ws)["limits"]["workflows"] == {"used": 5, "max": 5}


def test_free_plan_seat_limit(free_ws, signup):
    client, headers, base, _ = free_ws
    signup("teammate@example.com")

    response = client.post(f"{base}/members", json={"email": "teammate@example.com", "role": "member"}, headers=headers)

    assert response.status_code == 409
    assert "seat" in response.json()["detail"]


# --- staff and checkout -----------------------------------------------------------

def test_plan_changes_are_staff_only(free_ws, signup, monkeypatch):
    client, headers, base, workspace_id = free_ws

    assert client.put(f"/admin/workspaces/{workspace_id}/plan", json={"plan": "business"}, headers=headers).status_code == 403

    monkeypatch.setenv("LUPHINA_STAFF_EMAILS", "staff@luphina.example")
    staff_headers, _ = signup("staff@luphina.example")
    response = client.put(f"/admin/workspaces/{workspace_id}/plan", json={"plan": "growth"}, headers=staff_headers)

    assert response.status_code == 200
    assert billing(free_ws)["plan"]["name"] == "growth"


def test_checkout_needs_stripe_and_owner(free_ws, monkeypatch):
    client, headers, base, _ = free_ws

    assert client.post(f"{base}/billing/checkout", json={"plan": "starter"}, headers=headers).status_code == 503

    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setenv("STRIPE_PRICE_STARTER", "price_starter")
    with patch("luphina.billing.stripe.requests.post") as post:
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"url": "https://checkout.stripe.example/s/1"}
        response = client.post(f"{base}/billing/checkout", json={"plan": "starter"}, headers=headers)

    assert response.json() == {"url": "https://checkout.stripe.example/s/1"}
    sent = post.call_args.kwargs["data"]
    assert sent["line_items[0][price]"] == "price_starter"
    assert sent["client_reference_id"] == str(free_ws[3])


# --- Stripe webhooks ------------------------------------------------------------

WEBHOOK_SECRET = "whsec_test_secret"


def stripe_post(client, event, secret=WEBHOOK_SECRET, timestamp=None):
    payload = json.dumps(event).encode()
    timestamp = str(int(timestamp or time.time()))
    signature = hmac.new(secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256).hexdigest()
    return client.post(
        "/billing/stripe-webhook",
        content=payload,
        headers={"Stripe-Signature": f"t={timestamp},v1={signature}"},
    )


@pytest.fixture
def stripe_env(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setenv("STRIPE_PRICE_STARTER", "price_starter")
    monkeypatch.setenv("STRIPE_PRICE_GROWTH", "price_growth")


def test_stripe_webhook_signature_is_required(client, stripe_env):
    event = {"id": "evt_1", "type": "invoice.paid", "data": {"object": {}}}

    assert stripe_post(client, event, secret="whsec_wrong").status_code == 400
    assert stripe_post(client, event, timestamp=time.time() - 3600).status_code == 400
    assert client.post("/billing/stripe-webhook", content=b"{}").status_code == 400


def test_stripe_subscription_lifecycle(free_ws, stripe_env):
    client, _, _, workspace_id = free_ws

    stripe_post(client, {"id": "evt_1", "type": "checkout.session.completed", "data": {"object": {
        "client_reference_id": str(workspace_id), "customer": "cus_1", "subscription": "sub_1",
        "metadata": {"plan": "starter"},
    }}})
    assert billing(free_ws)["plan"]["name"] == "starter"

    now = int(time.time())
    upgrade = {"id": "evt_2", "type": "customer.subscription.updated", "data": {"object": {
        "id": "sub_1", "customer": "cus_1", "status": "active", "cancel_at_period_end": False,
        "items": {"data": [{"price": {"id": "price_growth"},
                            "current_period_start": now - 86400, "current_period_end": now + 86400 * 29}]},
    }}}
    assert stripe_post(client, upgrade).json()["applied"] is True
    summary = billing(free_ws)
    assert summary["plan"]["name"] == "growth"
    assert summary["provider"] == "stripe"

    # Stripe delivers events at least once: duplicates are ignored
    assert stripe_post(client, upgrade).json()["applied"] is False

    stripe_post(client, {"id": "evt_3", "type": "invoice.payment_failed",
                         "data": {"object": {"customer": "cus_1", "subscription": "sub_1"}}})
    summary = billing(free_ws)
    assert summary["status"] == "past_due"
    assert summary["plan"]["name"] == "growth"  # grace period keeps the plan
    assert any("payment failed" in alert for alert in summary["alerts"])

    stripe_post(client, {"id": "evt_4", "type": "invoice.paid",
                         "data": {"object": {"customer": "cus_1", "subscription": "sub_1"}}})
    assert billing(free_ws)["status"] == "active"

    stripe_post(client, {"id": "evt_5", "type": "customer.subscription.deleted", "data": {"object": {
        "id": "sub_1", "customer": "cus_1", "status": "canceled", "items": {"data": []},
    }}})
    summary = billing(free_ws)
    assert summary["status"] == "canceled"
    assert summary["plan"]["name"] == "free"


def test_signature_helper_accepts_any_v1(monkeypatch):
    payload, now = b'{"a":1}', int(time.time())
    good = hmac.new(b"whsec_x", f"{now}.".encode() + payload, hashlib.sha256).hexdigest()

    stripe.verify_signature(payload, f"t={now},v1=deadbeef,v1={good}", secret="whsec_x")

    with pytest.raises(stripe.InvalidSignature):
        stripe.verify_signature(payload, f"t={now},v1=deadbeef", secret="whsec_x")
