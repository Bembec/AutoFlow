import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import update

from luphina.integrations import mcp
from luphina.storage.db import session_scope
from luphina.storage.models import Workspace

TOOLS = [
    {"name": "search_products", "description": "Find products", "annotations": {"readOnlyHint": True},
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}}},
    {"name": "create_discount", "description": "Make a discount code", "annotations": {"readOnlyHint": False}},
    {"name": "delete_everything", "description": "Not allowed here"},
]


class FakeServer:
    """Answers MCP JSON-RPC like a real Streamable HTTP server."""

    def __init__(self, stream=False):
        self.stream = stream
        self.calls = []

    def post(self, url, json=None, headers=None, **kwargs):  # noqa: A002 - mirrors requests.post
        self.calls.append((json, headers))
        method = json.get("method")
        if "id" not in json:  # a notification
            return self._reply(None, status=202)
        if method == "initialize":
            result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "fake"}}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            name = json["params"]["name"]
            if name == "search_products":
                query = json["params"]["arguments"].get("query")
                result = {"content": [{"type": "text", "text": f"2 mugs match {query}"}],
                          "structuredContent": {"count": 2}}
            elif name == "create_discount":
                result = {"content": [{"type": "text", "text": "Code SPRING10 created"}]}
            else:
                result = {"content": [{"type": "text", "text": "boom"}], "isError": True}
        else:
            return self._reply({"jsonrpc": "2.0", "id": json["id"], "error": {"code": -32601, "message": "no"}})
        return self._reply({"jsonrpc": "2.0", "id": json["id"], "result": result})

    def _reply(self, message, status=200):
        response = MagicMock(status_code=status)
        response.headers = {"Mcp-Session-Id": "session-123"}
        if self.stream and message:
            response.headers["Content-Type"] = "text/event-stream"
            response.text = f"event: message\ndata: {json.dumps(message)}\n\n"
        else:
            response.headers["Content-Type"] = "application/json"
            response.json.return_value = message
        return response


@pytest.fixture
def server():
    fake = FakeServer()
    with patch("luphina.integrations.mcp.requests.post", side_effect=fake.post), \
            patch("luphina.integrations.mcp.check_public_url"), \
            patch("luphina.engine.executor.sleep"):
        yield fake


@pytest.fixture
def ws(client, signup, server):
    headers, workspace_id = signup()
    with session_scope() as session:
        session.execute(update(Workspace).where(Workspace.id == workspace_id).values(feature_flags={"mcp_tools": True}))
    base = f"/workspaces/{workspace_id}"
    connection = client.post(f"{base}/connections", json={
        "provider": "mcp", "name": "catalog",
        "config": {"server_url": "https://mcp.shop-tools.example/mcp", "allowed_tools": "search_products, create_discount"},
        "secrets": {"token": "mcp-token-123456"},
    }, headers=headers)
    assert connection.status_code == 201, connection.text
    return client, headers, base, connection.json()


def flow(ws, steps):
    client, headers, base, _ = ws
    created = client.post(f"{base}/workflows", json={"name": "MCP", "definition": {"steps": steps}}, headers=headers)
    assert created.status_code == 201, created.text
    client.post(f"{base}/workflows/{created.json()['id']}/publish", headers=headers)
    return created.json()


def run(ws, workflow, mode="live", payload=None):
    client, headers, base, _ = ws
    return client.post(f"{base}/workflows/{workflow['id']}/executions",
                       json={"mode": mode, "payload": payload or {}}, headers=headers).json()


def test_client_speaks_json_rpc_and_reads_event_streams(server):
    for stream in (False, True):
        server.stream = stream
        result = mcp.call({"server_url": "https://mcp.example/mcp", "allowed_tools": "*"}, {"token": "t"},
                          "search_products", {"query": "mug"}, read_only=True)
        assert result == {"tool": "search_products", "text": "2 mugs match mug", "data": {"count": 2}}

    first, then = server.calls[0], server.calls[1]
    assert first[0]["method"] == "initialize" and first[1]["Authorization"] == "Bearer t"
    assert then[0] == {"jsonrpc": "2.0", "method": "notifications/initialized"}
    assert then[1]["Mcp-Session-Id"] == "session-123"


def test_only_https_public_servers():
    with pytest.raises(mcp.MCPError, match="https"):
        mcp.check_server_url("http://mcp.example/mcp")
    with pytest.raises(mcp.MCPError):
        mcp.check_server_url("https://127.0.0.1/mcp")


def test_lists_tools_and_what_is_allowed(ws):
    client, headers, base, connection = ws
    tools = {t["name"]: t for t in client.get(f"{base}/connections/{connection['id']}/mcp-tools", headers=headers).json()}
    assert tools["search_products"]["read_only"] is True and tools["search_products"]["allowed"] is True
    assert tools["delete_everything"]["allowed"] is False
    assert client.post(f"{base}/connections/{connection['id']}/check", headers=headers).json()["ok"] is True


def test_read_step_runs_read_only_tools_even_in_test_runs(ws):
    workflow = flow(ws, [{"id": "find", "action": "mcp_read",
                          "inputs": {"connection": "catalog", "tool": "search_products", "arguments": {"query": "{{trigger.q}}"}}}])
    done = run(ws, workflow, mode="test", payload={"q": "blue"})
    assert done["status"] == "succeeded"
    assert done["steps"][0]["output"]["text"] == "2 mugs match blue"


def test_read_step_refuses_tools_that_change_things_and_unlisted_tools(ws):
    changing = run(ws, flow(ws, [{"id": "x", "action": "mcp_read",
                                  "inputs": {"connection": "catalog", "tool": "create_discount"}}]))
    assert changing["status"] == "failed" and "can't run as a read" in changing["error"]
    unlisted = run(ws, flow(ws, [{"id": "x", "action": "mcp_read",
                                  "inputs": {"connection": "catalog", "tool": "delete_everything"}}]))
    assert unlisted["status"] == "failed" and "allowed tools" in unlisted["error"]


def test_tools_that_change_things_always_wait_for_approval(ws, server):
    client, headers, base, _ = ws
    workflow = flow(ws, [{"id": "code", "action": "mcp_call_tool",
                          "inputs": {"connection": "catalog", "tool": "create_discount", "arguments": {"percent": 10}}}])
    tested = run(ws, workflow, mode="test")
    assert tested["steps"][0]["output"]["dry_run"] is True

    calls_before = len(server.calls)
    waiting = run(ws, workflow)
    assert waiting["status"] == "waiting_approval" and len(server.calls) == calls_before
    approval = client.get(f"{base}/approvals", headers=headers).json()[0]
    client.post(f"{base}/approvals/{approval['id']}/approve", headers=headers)
    done = client.get(f"{base}/executions/{waiting['id']}", headers=headers).json()
    assert done["status"] == "succeeded" and done["steps"][0]["output"]["text"] == "Code SPRING10 created"

    with pytest.raises(Exception, match="always requires human approval"):
        from luphina.engine.definition import WorkflowDefinition
        WorkflowDefinition.model_validate({"steps": [{"id": "c", "action": "mcp_call_tool", "requires_approval": False,
                                                      "inputs": {"connection": "catalog", "tool": "create_discount"}}]})


def test_mcp_needs_the_feature(client, signup, server, monkeypatch):
    monkeypatch.setenv("LUPHINA_FEATURES", "mcp_tools=off")
    headers, workspace_id = signup(email="plain@example.com")
    base = f"/workspaces/{workspace_id}"
    refused = client.post(f"{base}/connections", json={
        "provider": "mcp", "name": "catalog",
        "config": {"server_url": "https://mcp.shop-tools.example/mcp", "allowed_tools": "*"},
    }, headers=headers)
    assert refused.status_code == 403
    saved = client.post(f"{base}/workflows", json={"name": "M", "definition": {"steps": [
        {"id": "f", "action": "mcp_read", "inputs": {"connection": "catalog", "tool": "search_products"}}]}}, headers=headers)
    assert saved.status_code == 403 and "MCP tools" in saved.json()["detail"]
