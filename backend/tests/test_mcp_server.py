from unittest.mock import patch

import pytest
from sqlalchemy import func, select, update

from autoflow.storage.db import session_scope
from autoflow.storage.models import AuditEvent, Workspace


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("autoflow.engine.executor.sleep"):
        yield


def switch_on(workspace_id):
    with session_scope() as session:
        session.execute(update(Workspace).where(Workspace.id == workspace_id).values(feature_flags={"mcp_server": True}))


@pytest.fixture
def shop(client, signup):
    headers, workspace_id = signup()
    switch_on(workspace_id)
    base = f"/workspaces/{workspace_id}"
    created = client.post(f"{base}/api-keys", json={"name": "Claude"}, headers=headers)
    assert created.status_code == 201
    key = created.json()["key"]
    return client, headers, base, {"Authorization": f"Bearer {key}"}


def rpc(client, auth, method, params=None, message_id=1):
    body = {"jsonrpc": "2.0", "method": method, "params": params or {}}
    if message_id is not None:
        body["id"] = message_id
    return client.post("/mcp", json=body, headers=auth)


def workflow(client, headers, base, steps, sample=None, enable=True):
    definition = {"trigger": {"type": "manual", "sample_payload": sample or {"customer": "Ada", "amount": 12}},
                  "steps": steps}
    created = client.post(f"{base}/workflows", json={"name": "Tag VIP order", "description": "Marks an order as VIP.",
                                                     "definition": definition}, headers=headers).json()
    client.post(f"{base}/workflows/{created['id']}/publish", headers=headers)
    if enable:
        client.patch(f"{base}/workflows/{created['id']}", json={"mcp_enabled": True}, headers=headers)
    return created


LOG = [{"id": "log", "action": "log_activity", "inputs": {"message": "VIP: {{trigger.customer}}"}}]


def test_keys_are_shown_once_and_stored_hashed(shop):
    client, headers, base, auth = shop
    listed = client.get(f"{base}/api-keys", headers=headers).json()
    assert listed["server_url"].endswith("/mcp")
    assert listed["keys"][0]["prefix"].startswith("afk_") and "key" not in listed["keys"][0]


def test_handshake_and_only_opted_in_workflows_become_tools(shop):
    client, headers, base, auth = shop
    hello = rpc(client, auth, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                             "clientInfo": {"name": "test", "version": "1"}}).json()["result"]
    assert hello["serverInfo"]["name"] == "Luphina" and hello["protocolVersion"] == "2025-06-18"
    assert rpc(client, auth, "notifications/initialized", message_id=None).status_code == 202
    assert rpc(client, auth, "ping").json()["result"] == {}

    workflow(client, headers, base, LOG, enable=False)
    names = [tool["name"] for tool in rpc(client, auth, "tools/list").json()["result"]["tools"]]
    assert names == ["list_recent_runs", "get_run"]

    opted = workflow(client, headers, base, LOG)
    tools = {tool["name"]: tool for tool in rpc(client, auth, "tools/list").json()["result"]["tools"]}
    run_tool = tools[f"run_tag_vip_order_{opted['id']}"]
    assert run_tool["inputSchema"]["properties"]["customer"] == {"type": "string"}
    assert run_tool["inputSchema"]["properties"]["amount"] == {"type": "number"}
    assert run_tool["annotations"]["readOnlyHint"] is False and tools["get_run"]["annotations"]["readOnlyHint"] is True


def test_running_a_workflow_once_even_if_asked_twice(shop):
    client, headers, base, auth = shop
    opted = workflow(client, headers, base, LOG)
    call = {"name": f"run_tag_vip_order_{opted['id']}", "arguments": {"customer": "Grace", "idempotency_key": "order-77"}}

    first = rpc(client, auth, "tools/call", call).json()["result"]
    again = rpc(client, auth, "tools/call", call).json()["result"]
    assert first["isError"] is False and first["structuredContent"]["status"] == "succeeded"
    assert again["structuredContent"]["run_id"] == first["structuredContent"]["run_id"]
    assert again["content"][0]["text"].startswith("Already started earlier")
    with session_scope() as session:
        assert session.scalar(select(func.count(AuditEvent.id)).where(AuditEvent.action == "mcp.run_workflow")) == 1

    run = rpc(client, auth, "tools/call", {"name": "get_run", "arguments": {"run_id": first["structuredContent"]["run_id"]}})
    assert run.json()["result"]["structuredContent"]["steps"][0]["status"] == "succeeded"
    recent = rpc(client, auth, "tools/call", {"name": "list_recent_runs", "arguments": {}}).json()["result"]
    assert len(recent["structuredContent"]["runs"]) == 1


def test_approvals_still_apply(shop):
    client, headers, base, auth = shop
    email = [{"id": "send", "action": "send_email", "inputs": {"to": "a@b.co", "subject": "Hi", "body": "Thanks"}}]
    opted = workflow(client, headers, base, email)
    result = rpc(client, auth, "tools/call", {"name": f"run_tag_vip_order_{opted['id']}", "arguments": {}}).json()["result"]
    assert result["structuredContent"]["status"] == "waiting_approval"
    assert "waiting for a person to approve" in result["content"][0]["text"]


def test_assistants_see_only_what_they_may(shop, client, signup):
    _, headers, base, auth = shop
    hidden = workflow(client, headers, base, LOG, enable=False)
    run = client.post(f"{base}/workflows/{hidden['id']}/executions", json={"mode": "live"}, headers=headers).json()
    refused = rpc(client, auth, "tools/call", {"name": "get_run", "arguments": {"run_id": run["id"]}}).json()["result"]
    assert refused["isError"] is True
    unknown = rpc(client, auth, "tools/call", {"name": f"run_tag_vip_order_{hidden['id']}", "arguments": {}}).json()
    assert unknown["result"]["isError"] is True
    assert rpc(client, auth, "resources/list").json()["error"]["code"] == -32601

    other_headers, other_id = signup(email="other@example.com")
    switch_on(other_id)
    other_key = client.post(f"/workspaces/{other_id}/api-keys", json={"name": "x"}, headers=other_headers).json()["key"]
    other = {"Authorization": f"Bearer {other_key}"}
    assert rpc(client, other, "tools/call", {"name": "get_run", "arguments": {"run_id": run["id"]}}).json()["result"]["isError"]


def test_keys_switch_and_revocation(shop, client, signup):
    _, headers, base, auth = shop
    assert rpc(client, {"Authorization": "Bearer afk_wrong"}, "ping").status_code == 401
    assert rpc(client, {}, "ping").status_code == 401
    assert client.get("/mcp").status_code == 405

    key_id = client.get(f"{base}/api-keys", headers=headers).json()["keys"][0]["id"]
    client.delete(f"{base}/api-keys/{key_id}", headers=headers)
    assert rpc(client, auth, "ping").status_code == 401

    plain_headers, plain_id = signup(email="plain@example.com")
    with session_scope() as session:
        session.execute(update(Workspace).where(Workspace.id == plain_id).values(feature_flags={"mcp_server": False}))
    assert client.post(f"/workspaces/{plain_id}/api-keys", json={"name": "x"}, headers=plain_headers).status_code == 403
