import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, update

from luphina.engine import executor
from luphina.engine.definition import WorkflowDefinition, uses_smarter_logic
from luphina.engine.templating import evaluate_condition
from luphina.storage.db import engine as db_engine
from luphina.storage.db import session_scope
from luphina.storage.models import BillableEvent, StepExecution, WorkflowExecution, Workspace

ORDER = {
    "total": "247.50",
    "tags": "gift, rush",
    "line_items": [
        {"sku": "MUG-1", "title": "Ceramic mug", "quantity": 2},
        {"sku": "BEAN-2", "title": "Coffee beans", "quantity": 1},
        {"sku": "TOTE-3", "title": "Linen tote", "quantity": 1},
    ],
}


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("luphina.engine.executor.sleep"):
        yield


@pytest.fixture
def ws(client, signup):
    headers, workspace_id = signup()
    with session_scope() as session:
        session.execute(update(Workspace).where(Workspace.id == workspace_id)
                        .values(feature_flags={"smarter_logic": True}))
    return client, headers, f"/workspaces/{workspace_id}", workspace_id


def check(when, context=None):
    step = WorkflowDefinition.model_validate(
        {"steps": [{"id": "s", "action": "log_activity", "inputs": {"message": "x"}, "when": when}]}
    ).steps[0]
    return evaluate_condition(step.when, {"trigger": ORDER, "steps": {}, **(context or {})})


# --- conditions -----------------------------------------------------------------

def test_comparisons_use_numbers_from_text():
    assert check({"left": "{{trigger.total}}", "op": "gt", "right": 200}) is True
    assert check({"left": "{{trigger.total}}", "op": "lte", "right": "247.5"}) is True
    assert check({"left": "{{trigger.total}}", "op": "lt", "right": 100}) is False
    # Not a number: simply false, never an error
    assert check({"left": "{{trigger.tags}}", "op": "gt", "right": 1}) is False
    assert check({"left": "{{trigger.missing}}", "op": "gte", "right": 0}) is False


def test_not_contains_and_nested_groups():
    assert check({"left": "{{trigger.tags}}", "op": "not_contains", "right": "wholesale"}) is True
    assert check({"left": "{{trigger.tags}}", "op": "not_contains", "right": "GIFT"}) is False
    vip_gift = {"all": [
        {"left": "{{trigger.total}}", "op": "gt", "right": 200},
        {"any": [
            {"left": "{{trigger.tags}}", "op": "contains", "right": "vip"},
            {"left": "{{trigger.tags}}", "op": "contains", "right": "gift"},
        ]},
    ]}
    assert check(vip_gift) is True
    assert check({"any": [{"left": "{{trigger.total}}", "op": "lt", "right": 10},
                          {"left": "{{trigger.tags}}", "op": "eq", "right": "nope"}]}) is False


def test_definitions_are_checked():
    def definition(step):
        return WorkflowDefinition.model_validate({"steps": [{"id": "s", "inputs": {"message": "m"}, **step}]})

    assert uses_smarter_logic(definition({"action": "log_activity", "for_each": "{{trigger.line_items}}"}))
    assert not uses_smarter_logic(definition({"action": "log_activity",
                                              "when": {"left": "{{trigger.a}}", "op": "eq", "right": 1}}))
    for bad, message in [
        ({"action": "log_activity", "for_each": "trigger.line_items"}, "one reference"),
        ({"action": "log_activity", "when": {"all": []}}, "at least 1"),
        ({"action": "log_activity", "when": {"all": [{"left": 1, "op": "eq"}], "any": [{"left": 1, "op": "eq"}]}}, "either"),
        ({"action": "log_activity", "inputs": {"message": "{{item.title}}"}}, "earlier step"),
        ({"action": "log_activity", "for_each": "{{trigger.items}}", "inputs": {"message": "m"},
          "when": {"left": "{{item.title}}", "op": "exists"}}, "earlier step"),
    ]:
        with pytest.raises(ValidationError, match=message):
            definition(bad)
    with pytest.raises(ValidationError, match="can't run in a loop"):
        WorkflowDefinition.model_validate({"steps": [{
            "id": "s", "action": "send_email", "for_each": "{{trigger.items}}",
            "inputs": {"to": "{{item.email}}", "subject": "s", "body": "b"},
        }]})


def test_the_feature_flag_guards_saving(client, signup, monkeypatch):
    monkeypatch.setenv("LUPHINA_FEATURES", "smarter_logic=off")
    headers, workspace_id = signup()
    smart = {"name": "Smart", "definition": {"steps": [{
        "id": "s", "action": "log_activity", "inputs": {"message": "big"},
        "when": {"left": "{{trigger.total}}", "op": "gt", "right": 100},
    }]}}
    refused = client.post(f"/workspaces/{workspace_id}/workflows", json=smart, headers=headers)
    assert refused.status_code == 403 and "not switched on" in refused.json()["detail"]

    with session_scope() as session:
        session.execute(update(Workspace).where(Workspace.id == workspace_id)
                        .values(feature_flags={"smarter_logic": True}))
    assert client.post(f"/workspaces/{workspace_id}/workflows", json=smart, headers=headers).status_code == 201


# --- loops ----------------------------------------------------------------------

def flow(ws, steps):
    client, headers, base, _ = ws
    workflow = client.post(f"{base}/workflows", json={"name": "Loop", "definition": {"steps": steps}}, headers=headers)
    assert workflow.status_code == 201, workflow.text
    client.post(f"{base}/workflows/{workflow.json()['id']}/publish", headers=headers)
    return workflow.json()


def run(ws, workflow, payload=ORDER, mode="live"):
    client, headers, base, _ = ws
    return client.post(f"{base}/workflows/{workflow['id']}/executions",
                       json={"mode": mode, "payload": payload}, headers=headers).json()


def test_for_each_runs_once_per_item_and_later_steps_see_the_results(ws):
    workflow = flow(ws, [
        {"id": "lines", "action": "log_activity", "for_each": "{{trigger.line_items}}",
         "inputs": {"message": "{{index}}: {{item.quantity}} x {{item.title}}"}},
        {"id": "total", "action": "log_activity", "inputs": {"message": "{{steps.lines.output.count}} lines"},
         "when": {"left": "{{steps.lines.output.count}}", "op": "gte", "right": 2}},
    ])
    done = run(ws, workflow)

    assert done["status"] == "succeeded"
    steps = {s["step_id"]: s for s in done["steps"]}
    assert steps["lines"]["output"]["count"] == 3
    assert [i["message"] for i in steps["lines"]["input"]["items"]] == [
        "0: 2 x Ceramic mug", "1: 1 x Coffee beans", "2: 1 x Linen tote"]
    assert steps["total"]["status"] == "succeeded"

    empty = run(ws, workflow, {"line_items": []})
    assert {s["step_id"]: s for s in empty["steps"]}["lines"]["output"] == {"items": [], "count": 0}


def test_too_many_items_fail_clearly(ws):
    workflow = flow(ws, [{"id": "lines", "action": "log_activity", "for_each": "{{trigger.rows}}",
                          "inputs": {"message": "{{item}}"}}])
    failed = run(ws, workflow, {"rows": list(range(101))})
    assert failed["status"] == "failed" and "at most 100 items" in failed["error"]
    assert run(ws, workflow, {"rows": "not a list"})["status"] == "failed"


def api_loop(ws):
    client, headers, base, _ = ws
    client.post(f"{base}/connections", json={
        "provider": "http", "name": "warehouse",
        "config": {"header_name": "X-Api-Key", "base_url": "https://warehouse.example/api"},
        "secrets": {"header_value": "key-abcdef-123456"},
    }, headers=headers)
    return flow(ws, [{"id": "send", "action": "http_send", "for_each": "{{trigger.line_items}}",
                      "inputs": {"connection": "warehouse", "url": "/stock", "body": {"sku": "{{item.sku}}"}}}])


def response(status):
    reply = MagicMock(status_code=status, ok=status < 400, headers={"Content-Type": "application/json"})
    reply.json.return_value = {"ok": status < 400}
    reply.text = json.dumps({"ok": status < 400})
    return reply


def test_a_failed_loop_resumes_without_repeating_finished_items(ws):
    client, headers, base, workspace_id = ws
    workflow = api_loop(ws)
    with patch("luphina.integrations.actions.check_public_url"), \
            patch("luphina.integrations.actions.requests") as http:
        http.request.side_effect = [response(200), response(400)]
        failed = run(ws, workflow)
        assert failed["status"] == "failed" and "item 2" in failed["error"]

        http.request.side_effect = [response(200), response(200)]
        done = client.post(f"{base}/executions/{failed['id']}/retry", headers=headers).json()

    sent = [call.kwargs["json"] for call in http.request.call_args_list]
    assert [body["sku"] for body in sent] == ["MUG-1", "BEAN-2", "BEAN-2", "TOTE-3"]
    assert done["status"] == "succeeded" and done["steps"][0]["output"]["count"] == 3

    with session_scope() as session:
        billed = session.scalar(select(func.sum(BillableEvent.quantity)).where(BillableEvent.workspace_id == workspace_id))
    assert billed == 3


def test_an_uncertain_loop_item_can_be_confirmed_and_the_loop_continues(ws):
    client, headers, base, _ = ws
    workflow = api_loop(ws)
    with patch("luphina.integrations.actions.check_public_url"), \
            patch("luphina.integrations.actions.requests") as http:
        http.request.side_effect = [response(200)] * 3
        started = run(ws, workflow, mode="live")
        # Pretend the worker died while sending item 2 (item 1 already done)
        with db_engine.begin() as connection:
            connection.execute(update(StepExecution).where(StepExecution.execution_id == started["id"]).values(
                status="running", output={"items": [{"status": 200}], "count": 1, "in_progress": True}))
            connection.execute(update(WorkflowExecution).where(WorkflowExecution.id == started["id"])
                               .values(status="running"))
        http.request.reset_mock()
        http.request.side_effect = [response(200)] * 3
        with session_scope() as session:
            executor.execute(session, session.get(WorkflowExecution, started["id"]))
        assert client.get(f"{base}/executions/{started['id']}", headers=headers).json()["status"] == "needs_attention"

        done = client.post(f"{base}/executions/{started['id']}/confirm-done", headers=headers).json()

    assert done["status"] == "succeeded"
    items = done["steps"][0]["output"]["items"]
    assert len(items) == 3 and items[1] == {"confirmed_by_person": True}
    assert http.request.call_count == 1  # only item 3 was sent after the crash
