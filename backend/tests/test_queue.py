from datetime import timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import update

from luphina.engine import queue
from luphina.integrations import webhooks
from luphina.storage.db import engine as db_engine
from luphina.storage.db import session_scope, utc_now
from luphina.storage.models import StepExecution, WorkflowExecution


@pytest.fixture(autouse=True)
def fakes():
    with (
        patch("luphina.engine.executor.sleep"),
        patch("luphina.engine.actions.send_email", return_value=True) as send,
    ):
        yield send


@pytest.fixture
def queue_mode(monkeypatch):
    monkeypatch.setenv("LUPHINA_EXECUTION_MODE", "queue")


@pytest.fixture
def ws(client, signup):
    headers, workspace_id = signup()
    return client, headers, f"/workspaces/{workspace_id}"


def create(ws, steps, trigger=None):
    client, headers, base = ws
    definition = {"steps": steps, **({"trigger": trigger} if trigger else {})}
    workflow = client.post(f"{base}/workflows", json={"name": "Q", "definition": definition}, headers=headers).json()
    client.post(f"{base}/workflows/{workflow['id']}/publish", headers=headers)
    return workflow


def start(ws, workflow_id, mode="live"):
    client, headers, base = ws
    return client.post(f"{base}/workflows/{workflow_id}/executions", json={"mode": mode}, headers=headers).json()


def get(ws, execution_id):
    client, headers, base = ws
    return client.get(f"{base}/executions/{execution_id}", headers=headers).json()


def work(limit=10):
    with session_scope() as session:
        return queue.run_due(session, "test-worker", limit=limit)


LOG = {"id": "log", "action": "log_activity", "inputs": {"message": "hello"}}
DELAYED = [
    {"id": "first", "action": "log_activity", "inputs": {"message": "before"}},
    {"id": "wait", "action": "delay", "inputs": {"hours": 2}},
    {"id": "after", "action": "log_activity", "inputs": {"message": "after"}},
]


def make_due(execution_id):
    """Pretend the delay has passed."""

    past = utc_now() - timedelta(minutes=1)
    with db_engine.begin() as connection:
        connection.execute(update(WorkflowExecution).where(WorkflowExecution.id == execution_id).values(run_after=past))
        connection.execute(
            update(StepExecution)
            .where(StepExecution.execution_id == execution_id, StepExecution.action == "delay")
            .values(output={"resume_at": past.isoformat()})
        )


# --- queue mode -----------------------------------------------------------------

def test_queue_mode_returns_immediately_and_workers_run_it(ws, queue_mode):
    workflow = create(ws, [LOG])

    queued = start(ws, workflow["id"])

    assert queued["status"] == "queued"
    assert queued["steps"] == []
    assert work() == 1
    assert get(ws, queued["id"])["status"] == "succeeded"
    assert work() == 0


def test_an_execution_is_claimed_only_once(ws, queue_mode):
    workflow = create(ws, [LOG])
    start(ws, workflow["id"])

    with session_scope() as session:
        first = queue.claim_next(session, "worker-a")
    with session_scope() as session:
        second = queue.claim_next(session, "worker-b")

    assert first is not None and first.claimed_by == "worker-a"
    assert second is None


def test_queue_mode_resumes_after_approval_in_the_worker(ws, queue_mode, fakes):
    client, headers, base = ws
    workflow = create(ws, [{"id": "send", "action": "send_email", "inputs": {"to": "a@b.co", "subject": "s", "body": "b"}}])
    execution = start(ws, workflow["id"])
    work()
    assert get(ws, execution["id"])["status"] == "waiting_approval"

    approval = client.get(f"{base}/approvals", params={"kind": "step", "status": "pending"}, headers=headers).json()[0]
    client.post(f"{base}/approvals/{approval['id']}/approve", headers=headers)

    # The API only re-queued it; nothing was sent inside the request
    assert get(ws, execution["id"])["status"] == "queued"
    fakes.assert_not_called()

    work()
    assert get(ws, execution["id"])["status"] == "succeeded"
    fakes.assert_called_once()


def test_webhooks_are_queued_in_queue_mode(ws, queue_mode):
    client, headers, base = ws
    workflow = create(ws, [LOG], trigger={"type": "webhook"})
    hook = client.post(f"{base}/workflows/{workflow['id']}/webhook", headers=headers).json()
    body = b"{}"

    response = client.post("/hooks/" + hook["url"].rsplit("/", 1)[1], content=body, headers=webhooks.sign(hook["secret"], body))

    assert response.status_code == 202
    assert response.json()["status"] == "queued"


# --- delay steps ------------------------------------------------------------------

def test_delay_parks_the_execution_until_due(ws):
    workflow = create(ws, DELAYED)

    execution = start(ws, workflow["id"])
    steps = {s["step_id"]: s for s in execution["steps"]}

    assert execution["status"] == "queued"
    assert steps["first"]["status"] == "succeeded"
    assert steps["wait"]["status"] == "waiting"
    assert "after" not in steps
    assert work() == 0  # not due yet

    make_due(execution["id"])
    assert work() == 1

    done = get(ws, execution["id"])
    steps = {s["step_id"]: s for s in done["steps"]}
    assert done["status"] == "succeeded"
    assert steps["after"]["status"] == "succeeded"
    # The step before the delay was not run twice
    assert steps["first"]["attempts"] == 1


def test_test_runs_skip_delays(ws):
    workflow = create(ws, DELAYED)

    execution = start(ws, workflow["id"], mode="test")

    assert execution["status"] == "succeeded"
    assert execution["steps"][1]["output"] == {"skipped_in_test": True}


@pytest.mark.parametrize("inputs, message", [
    ({"minutes": 0}, "greater than 0"),
    ({"days": 45}, "at most 30 days"),
])
def test_invalid_delays_fail(ws, inputs, message):
    workflow = create(ws, [{"id": "wait", "action": "delay", "inputs": inputs}])

    execution = start(ws, workflow["id"])

    assert execution["status"] == "failed"
    assert message in execution["error"]


def test_cancelling_a_delayed_execution(ws):
    client, headers, base = ws
    workflow = create(ws, DELAYED)
    execution = start(ws, workflow["id"])

    client.post(f"{base}/executions/{execution['id']}/cancel", headers=headers)
    make_due(execution["id"])

    assert work() == 0
    assert get(ws, execution["id"])["status"] == "cancelled"


# --- crash recovery ----------------------------------------------------------------

def simulate_crash(execution_id, step_action):
    """A worker died mid-step: execution running, step running, stale heartbeat."""

    stale = utc_now() - timedelta(hours=1)
    with db_engine.begin() as connection:
        connection.execute(
            update(WorkflowExecution).where(WorkflowExecution.id == execution_id)
            .values(status="running", heartbeat_at=stale, claimed_by="dead-worker")
        )
        connection.execute(
            update(StepExecution)
            .where(StepExecution.execution_id == execution_id, StepExecution.action == step_action)
            .values(status="running", attempts=1)
        )


def test_stale_execution_is_recovered_and_finished(ws, queue_mode):
    workflow = create(ws, [LOG])
    execution = start(ws, workflow["id"])
    work()
    with db_engine.begin() as connection:
        connection.execute(update(StepExecution).where(StepExecution.execution_id == execution["id"])
                           .values(status="pending"))
    simulate_crash(execution["id"], "log_activity")

    with session_scope() as session:
        assert queue.recover_stale(session) == 1
    work()

    assert get(ws, execution["id"])["status"] == "succeeded"


def test_crashed_email_send_is_not_repeated(ws, queue_mode, fakes):
    client, headers, base = ws
    workflow = create(ws, [{"id": "send", "action": "send_email", "inputs": {"to": "a@b.co", "subject": "s", "body": "b"}}])
    execution = start(ws, workflow["id"])
    work()
    approval = client.get(f"{base}/approvals", params={"kind": "step", "status": "pending"}, headers=headers).json()[0]
    client.post(f"{base}/approvals/{approval['id']}/approve", headers=headers)
    simulate_crash(execution["id"], "send_email")

    with session_scope() as session:
        queue.recover_stale(session)
    work()

    assert get(ws, execution["id"])["status"] == "needs_attention"
    fakes.assert_not_called()


def test_fresh_heartbeats_are_not_recovered(ws, queue_mode):
    workflow = create(ws, [LOG])
    execution = start(ws, workflow["id"])
    with db_engine.begin() as connection:
        connection.execute(update(WorkflowExecution).where(WorkflowExecution.id == execution["id"])
                           .values(status="running", heartbeat_at=utc_now()))

    with session_scope() as session:
        assert queue.recover_stale(session) == 0
