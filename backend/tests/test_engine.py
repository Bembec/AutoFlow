import time
from unittest.mock import patch

import pytest

from autoflow.engine.actions import ActionError


@pytest.fixture(autouse=True)
def engine_fakes():
    """No real waiting, exchange-rate calls or emails during engine tests."""

    with (
        patch("autoflow.engine.executor.sleep"),
        patch("autoflow.engine.actions.fetch_eur_to_usd", return_value=(1.1, "2026-10-21")) as rate,
        patch("autoflow.engine.actions.send_email", return_value=True) as send,
    ):
        yield {"rate": rate, "send": send}


@pytest.fixture
def ws(client, signup):
    headers, workspace_id = signup()
    return client, headers, f"/workspaces/{workspace_id}"


def install_template(ws):
    client, headers, base = ws
    response = client.post(
        f"{base}/workflows/from-template",
        json={"template": "customer-enquiry-triage"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def start(ws, workflow_id, mode="live", payload=None, key=None):
    client, headers, base = ws
    extra = {"Idempotency-Key": key} if key else {}
    body = {"mode": mode}
    if payload is not None:
        body["payload"] = payload
    return client.post(
        f"{base}/workflows/{workflow_id}/executions",
        json=body,
        headers={**headers, **extra},
    )


def publish(ws, workflow_id, version=None):
    client, headers, base = ws
    body = {"version": version} if version else None
    return client.post(f"{base}/workflows/{workflow_id}/publish", json=body, headers=headers)


def steps_by_id(execution):
    return {step["step_id"]: step for step in execution["steps"]}


def pending_step_approval(ws, execution_id):
    client, headers, base = ws
    approvals = client.get(
        f"{base}/approvals", params={"kind": "step", "status": "pending"}, headers=headers
    ).json()
    return next(a for a in approvals if a["execution_id"] == execution_id)


SUPPORT_ENQUIRY = {"name": "James", "email": "james@example.com", "message": "I need help"}


# --- definitions -----------------------------------------------------------

@pytest.mark.parametrize(
    "steps, problem",
    [
        ([{"id": "a", "action": "nope", "inputs": {}}], "unknown action"),
        ([{"id": "a", "action": "log_activity", "inputs": {"message": "x"}},
          {"id": "a", "action": "log_activity", "inputs": {"message": "y"}}], "Duplicate step id"),
        ([{"id": "a", "action": "log_activity", "inputs": {"message": "{{steps.b.output.x}}"}},
          {"id": "b", "action": "log_activity", "inputs": {"message": "y"}}], "earlier step"),
        ([{"id": "a", "action": "compose_email", "inputs": {"name": "x"}}], "missing inputs"),
        ([{"id": "a", "action": "send_email", "requires_approval": False,
           "inputs": {"to": "a@b.c", "subject": "s", "body": "b"}}], "always requires human approval"),
    ],
)
def test_invalid_definitions_are_rejected(ws, steps, problem):
    client, headers, base = ws

    response = client.post(
        f"{base}/workflows",
        json={"name": "Bad", "definition": {"steps": steps}},
        headers=headers,
    )

    assert response.status_code == 422
    assert problem in response.text


def test_action_catalogue_and_templates(client):
    actions = {a["name"]: a for a in client.get("/actions").json()}

    assert actions["send_email"]["requires_approval"] is True
    assert "customer-enquiry-triage" in {t["slug"] for t in client.get("/templates").json()}


# --- test mode, publish, live ----------------------------------------------

def test_test_run_simulates_side_effects(ws, engine_fakes):
    client, headers, base = ws
    workflow = install_template(ws)

    response = start(ws, workflow["id"], mode="test")

    assert response.status_code == 201
    execution = response.json()
    assert execution["status"] == "succeeded"

    steps = steps_by_id(execution)
    assert steps["classify"]["output"]["category"] == "Sales"
    assert steps["quote"]["output"]["amount_usd"] == "110.00"
    assert steps["send"]["output"]["dry_run"] is True
    assert steps["save"]["output"]["dry_run"] is True

    # Nothing real happened
    engine_fakes["send"].assert_not_called()
    assert client.get(f"{base}/customers", headers=headers).json() == []


def test_live_run_needs_published_version(ws):
    workflow = install_template(ws)

    response = start(ws, workflow["id"])

    assert response.status_code == 409
    assert "Publish" in response.json()["detail"]


def test_live_run_waits_for_approval_then_sends_once(ws, engine_fakes):
    client, headers, base = ws
    workflow = install_template(ws)
    publish(ws, workflow["id"])

    execution = start(ws, workflow["id"], payload={
        "name": "Ada", "email": "ada@example.com", "message": "What is your price?",
    }).json()

    assert execution["status"] == "waiting_approval"
    assert steps_by_id(execution)["send"]["status"] == "waiting_approval"
    engine_fakes["send"].assert_not_called()

    # Steps before the gate already ran for real
    customers = client.get(f"{base}/customers", headers=headers).json()
    assert customers[0]["email"] == "ada@example.com"

    approval = pending_step_approval(ws, execution["id"])
    assert approval["customer_email"] == "ada@example.com"
    assert approval["payload"]["inputs"]["subject"] == "Information about our pricing"

    first = client.post(f"{base}/approvals/{approval['id']}/approve", headers=headers)
    second = client.post(f"{base}/approvals/{approval['id']}/approve", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 409
    engine_fakes["send"].assert_called_once()

    done = client.get(f"{base}/executions/{execution['id']}", headers=headers).json()
    assert done["status"] == "succeeded"
    assert steps_by_id(done)["send"]["output"]["sent"] is True


def test_rejecting_the_gate_cancels_the_execution(ws, engine_fakes):
    client, headers, base = ws
    workflow = install_template(ws)
    publish(ws, workflow["id"])
    execution = start(ws, workflow["id"], payload=SUPPORT_ENQUIRY).json()

    approval = pending_step_approval(ws, execution["id"])
    client.post(f"{base}/approvals/{approval['id']}/reject", headers=headers)

    done = client.get(f"{base}/executions/{execution['id']}", headers=headers).json()
    assert done["status"] == "cancelled"
    assert steps_by_id(done)["send"]["status"] == "rejected"
    engine_fakes["send"].assert_not_called()


def test_condition_skips_quote_for_support(ws, engine_fakes):
    workflow = install_template(ws)

    execution = start(ws, workflow["id"], mode="test", payload=SUPPORT_ENQUIRY).json()
    steps = steps_by_id(execution)

    assert steps["classify"]["output"]["category"] == "Support"
    assert steps["quote"]["status"] == "skipped"
    engine_fakes["rate"].assert_not_called()


def test_cancel_withdraws_pending_approval(ws):
    client, headers, base = ws
    workflow = install_template(ws)
    publish(ws, workflow["id"])
    execution = start(ws, workflow["id"], payload=SUPPORT_ENQUIRY).json()
    approval = pending_step_approval(ws, execution["id"])

    response = client.post(f"{base}/executions/{execution['id']}/cancel", headers=headers)

    assert response.json()["status"] == "cancelled"
    assert client.get(f"{base}/approvals/{approval['id']}", headers=headers).json()["status"] == "cancelled"
    assert client.post(f"{base}/executions/{execution['id']}/cancel", headers=headers).status_code == 409


# --- reliability -----------------------------------------------------------

def test_retries_then_succeeds(ws, engine_fakes):
    workflow = install_template(ws)
    engine_fakes["rate"].side_effect = [(None, None), (None, None), (1.2, "2026-10-21")]

    execution = start(ws, workflow["id"], mode="test").json()
    quote = steps_by_id(execution)["quote"]

    assert execution["status"] == "succeeded"
    assert quote["attempts"] == 3
    assert quote["output"]["amount_usd"] == "120.00"


def test_failed_execution_retries_from_failed_step(ws, engine_fakes):
    client, headers, base = ws
    workflow = install_template(ws)
    engine_fakes["rate"].return_value = (None, None)

    failed = start(ws, workflow["id"], mode="test").json()

    assert failed["status"] == "failed"
    assert steps_by_id(failed)["quote"]["attempts"] == 3
    assert "Exchange rate unavailable" in failed["error"]

    engine_fakes["rate"].return_value = (1.1, "2026-10-21")
    with patch("autoflow.engine.actions.classify_with_ai") as classifier:
        classifier.return_value = None
        retried = client.post(f"{base}/executions/{failed['id']}/retry", headers=headers).json()

    assert retried["status"] == "succeeded"
    # The classify step already succeeded, so it was not run again
    assert steps_by_id(retried)["classify"]["attempts"] == 1
    classifier.assert_not_called()


def test_idempotency_key_returns_the_same_execution(ws):
    client, headers, base = ws
    workflow = install_template(ws)

    first = start(ws, workflow["id"], mode="test", key="order-1001")
    second = start(ws, workflow["id"], mode="test", key="order-1001")

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert len(client.get(f"{base}/executions", headers=headers).json()) == 1


def test_uncertain_send_needs_attention_not_a_blind_retry(ws, engine_fakes):
    client, headers, base = ws
    definition = {
        "steps": [{
            "id": "send",
            "action": "send_email",
            "timeout_seconds": 1,
            "retry": {"max_attempts": 3},
            "inputs": {"to": "{{trigger.email}}", "subject": "Hi", "body": "Hello"},
        }]
    }
    workflow = client.post(
        f"{base}/workflows", json={"name": "Send", "definition": definition}, headers=headers
    ).json()
    publish(ws, workflow["id"])

    engine_fakes["send"].side_effect = lambda preview: time.sleep(1.5) or True
    execution = start(ws, workflow["id"], payload={"email": "ada@example.com"}).json()
    approval = pending_step_approval(ws, execution["id"])
    client.post(f"{base}/approvals/{approval['id']}/approve", headers=headers)

    stuck = client.get(f"{base}/executions/{execution['id']}", headers=headers).json()
    assert stuck["status"] == "needs_attention"
    # Not retried automatically, despite max_attempts 3
    assert steps_by_id(stuck)["send"]["attempts"] == 1

    blind = client.post(f"{base}/executions/{execution['id']}/retry", headers=headers)
    assert blind.status_code == 409

    engine_fakes["send"].side_effect = None
    confirmed = client.post(
        f"{base}/executions/{execution['id']}/retry",
        json={"confirm_not_completed": True},
        headers=headers,
    ).json()
    assert confirmed["status"] == "succeeded"


def test_bad_input_fails_without_retrying(ws, engine_fakes):
    client, headers, base = ws
    definition = {
        "steps": [{
            "id": "quote",
            "action": "exchange_rate_quote",
            "retry": {"max_attempts": 5},
            "inputs": {"amount_eur": "{{trigger.amount}}"},
        }]
    }
    workflow = client.post(
        f"{base}/workflows", json={"name": "Quote", "definition": definition}, headers=headers
    ).json()

    execution = start(ws, workflow["id"], mode="test", payload={"amount": "lots"}).json()

    assert execution["status"] == "failed"
    assert steps_by_id(execution)["quote"]["attempts"] == 1
    assert "must be a number" in execution["error"]


def test_action_error_class_is_retryable_by_default():
    assert ActionError("x").retryable is True


# --- versions --------------------------------------------------------------

def test_edit_after_publish_creates_new_draft_and_rollback(ws):
    client, headers, base = ws
    workflow = install_template(ws)
    publish(ws, workflow["id"])

    simple = {"steps": [{"id": "log", "action": "log_activity", "inputs": {"message": "v2"}}]}
    updated = client.patch(
        f"{base}/workflows/{workflow['id']}", json={"definition": simple}, headers=headers
    ).json()

    states = {v["number"]: v["state"] for v in updated["versions"]}
    assert states == {1: "published", 2: "draft"}

    publish(ws, workflow["id"])
    rolled_back = publish(ws, workflow["id"], version=1).json()

    states = {v["number"]: v["state"] for v in rolled_back["versions"]}
    assert states == {1: "published", 2: "archived"}

    assert publish(ws, workflow["id"]).status_code == 409  # no draft left


# --- access ---------------------------------------------------------------

def test_executions_are_isolated_between_workspaces(ws, signup):
    client, headers, base = ws
    workflow = install_template(ws)
    execution = start(ws, workflow["id"], mode="test").json()

    other_headers, other_workspace = signup("other@example.com")

    assert client.get(
        f"/workspaces/{other_workspace}/executions/{execution['id']}", headers=other_headers
    ).status_code == 404
    assert client.post(
        f"/workspaces/{other_workspace}/workflows/{workflow['id']}/executions",
        json={"mode": "test"},
        headers=other_headers,
    ).status_code == 404
