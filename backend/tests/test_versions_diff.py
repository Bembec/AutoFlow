from sqlalchemy import select

from luphina.engine.diff import compare
from luphina.storage.db import session_scope
from luphina.storage.models import AuditEvent

V1 = {
    "trigger": {"type": "webhook"},
    "steps": [
        {"id": "invoice", "action": "create_invoice", "inputs": {"order": "{{trigger}}"}},
        {"id": "log", "action": "log_activity", "inputs": {"message": "done"}},
        {"id": "old", "action": "log_activity", "inputs": {"message": "bye"}},
    ],
}
V2 = {
    "trigger": {"type": "webhook"},
    "steps": [
        {"id": "log", "name": "Log it", "action": "log_activity", "inputs": {"message": "invoice made"}},
        {"id": "invoice", "action": "create_invoice", "inputs": {"order": "{{trigger}}"},
         "when": {"left": "{{trigger.status}}", "op": "eq", "right": "paid"}},
        {"id": "new", "action": "log_activity", "inputs": {"message": "hello"}},
    ],
}


def test_compare_matches_steps_by_id():
    changes = {c.get("step_id", c["kind"]): c for c in compare(V1, V2)}

    assert changes["old"]["kind"] == "removed"
    assert changes["new"] == {**changes["new"], "kind": "added", "position": 3}
    log = changes["log"]
    assert log["kind"] == "changed" and log["moved"] is True
    assert {f["field"] for f in log["fields"]} == {"name", "inputs.message"}
    invoice = changes["invoice"]
    assert [f["field"] for f in invoice["fields"]] == ["when"] and invoice["fields"][0]["before"] is None
    assert "trigger" not in changes

    assert compare(V1, V1) == []
    schedule = compare(V1, {**V1, "trigger": {"type": "schedule", "schedule": "0 9 * * 1"}})
    assert schedule[0]["kind"] == "trigger" and {f["field"] for f in schedule[0]["fields"]} == {"type", "schedule"}


def test_compare_endpoint_defaults_to_live_versus_draft(client, signup):
    headers, workspace_id = signup()
    base = f"/workspaces/{workspace_id}"
    workflow = client.post(f"{base}/workflows", json={"name": "Flow", "definition": V1}, headers=headers).json()
    wid = workflow["id"]

    # Only a draft exists: nothing to compare against
    assert client.get(f"{base}/workflows/{wid}/compare", headers=headers).json() == {
        "before": None, "after": 1, "changes": []}

    client.post(f"{base}/workflows/{wid}/publish", headers=headers)
    client.patch(f"{base}/workflows/{wid}", json={"definition": V2}, headers=headers)
    pending = client.get(f"{base}/workflows/{wid}/compare", headers=headers).json()
    assert (pending["before"], pending["after"]) == (1, 2) and len(pending["changes"]) == 4

    client.post(f"{base}/workflows/{wid}/publish", headers=headers)
    with session_scope() as session:
        event = session.scalars(select(AuditEvent).where(AuditEvent.action == "workflow.published")
                                .order_by(AuditEvent.id.desc())).first()
    assert event.details["changes"] == 4 and event.details["steps_changed"] == ["invoice", "log", "new", "old"]

    # Any two versions, e.g. what a rollback to v1 would change
    rollback = client.get(f"{base}/workflows/{wid}/compare", params={"before": 2, "after": 1}, headers=headers).json()
    assert {c["kind"] for c in rollback["changes"]} == {"added", "removed", "changed"}
    assert client.get(f"{base}/workflows/{wid}/compare", params={"before": 9}, headers=headers).status_code == 404
