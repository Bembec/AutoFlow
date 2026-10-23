"""
A small MCP (Model Context Protocol) client: use tools from MCP servers.

Speaks JSON-RPC 2.0 over the Streamable HTTP transport:
initialize → notifications/initialized → tools/list or tools/call. Servers
may answer with plain JSON or a server-sent-event stream; both are read.

Safety rules (on top of the usual connection rules):
- https only, and never internal network addresses (SSRF guard);
- only tools the workspace admin listed in `allowed_tools` can be used;
- `mcp_read` only runs tools the server marks read-only (readOnlyHint);
  anything else goes through `mcp_call_tool`, which always needs approval;
- tool results are untrusted data and capped in size.
"""

import itertools
import json

import requests

from autoflow import __version__
from autoflow.security.net import UnsafeURL, check_public_url

PROTOCOL_VERSION = "2025-06-18"
MAX_RESULT_CHARS = 50_000
TIMEOUT_SECONDS = 30


class MCPError(Exception):
    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.retryable = retryable


def allowed_tools(config):
    """Tool names the admin allowed for this connection ("*" = every tool)."""
    raw = str(config.get("allowed_tools") or "").strip()
    return {"*"} if raw == "*" else {name.strip() for name in raw.split(",") if name.strip()}


def check_server_url(url):
    url = str(url or "").strip()
    if not url.startswith("https://"):
        raise MCPError("The MCP server address must start with https://")
    try:
        check_public_url(url)
    except UnsafeURL as error:
        raise MCPError(str(error)) from error
    return url


def _read_response(response, request_id):
    """The JSON-RPC reply with our id, from a JSON body or an SSE stream."""
    kind = response.headers.get("Content-Type", "")
    if "text/event-stream" in kind:
        for line in response.text.splitlines():
            if not line.startswith("data:"):
                continue
            try:
                message = json.loads(line[5:].strip())
            except ValueError:
                continue
            if isinstance(message, dict) and message.get("id") == request_id:
                return message
        raise MCPError("The MCP server's stream ended without an answer.", retryable=True)
    try:
        return response.json()
    except ValueError as error:
        raise MCPError("The MCP server sent something that isn't JSON.") from error


class Session:
    """One conversation with an MCP server (it may hand us a session id)."""

    def __init__(self, url, token=None):
        self.url = check_server_url(url)
        self.token = token
        self.session_id = None
        self.protocol = PROTOCOL_VERSION
        self._ids = itertools.count(1)

    def _headers(self):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": self.protocol,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _post(self, payload):
        try:
            response = requests.post(self.url, json=payload, headers=self._headers(), timeout=TIMEOUT_SECONDS,
                                     allow_redirects=False)
        except requests.RequestException as error:
            raise MCPError(f"Could not reach the MCP server: {error}", retryable=True) from error
        if response.status_code in (401, 403):
            raise MCPError(f"The MCP server rejected the credentials ({response.status_code}).")
        if response.status_code == 429 or response.status_code >= 500:
            raise MCPError(f"The MCP server is busy or failing ({response.status_code}).", retryable=True)
        if response.status_code >= 400:
            raise MCPError(f"The MCP server refused the request ({response.status_code}).")
        return response

    def request(self, method, params=None):
        request_id = next(self._ids)
        response = self._post({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})
        message = _read_response(response, request_id)
        if response.headers.get("Mcp-Session-Id"):
            self.session_id = response.headers["Mcp-Session-Id"]
        if "error" in message:
            error = message["error"] or {}
            raise MCPError(f"MCP error {error.get('code')}: {error.get('message')}")
        return message.get("result") or {}

    def start(self):
        result = self.request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "AutoFlow", "version": __version__},
        })
        self.protocol = result.get("protocolVersion") or PROTOCOL_VERSION
        # A notification has no id and no answer to wait for
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return result

    def list_tools(self):
        tools, cursor = [], None
        for _ in range(20):  # pages; servers rarely need more than one
            result = self.request("tools/list", {"cursor": cursor} if cursor else {})
            tools += result.get("tools") or []
            cursor = result.get("nextCursor")
            if not cursor:
                break
        return tools

    def call_tool(self, name, arguments):
        return self.request("tools/call", {"name": name, "arguments": arguments or {}})


def describe_tool(tool):
    annotations = tool.get("annotations") or {}
    return {
        "name": tool.get("name"),
        "description": tool.get("description") or "",
        "read_only": bool(annotations.get("readOnlyHint")),
        "input_schema": tool.get("inputSchema") or {},
    }


def list_tools(config, secrets):
    """Every tool the server offers, marked with whether this connection allows it."""
    session = Session(config.get("server_url"), secrets.get("token"))
    session.start()
    allowed = allowed_tools(config)
    return [{**describe_tool(tool), "allowed": "*" in allowed or tool.get("name") in allowed}
            for tool in session.list_tools()]


def call(config, secrets, tool, arguments, read_only):
    """Run one tool; returns {"text", "data", "tool"}."""
    tool = str(tool or "").strip()
    allowed = allowed_tools(config)
    if "*" not in allowed and tool not in allowed:
        raise MCPError(f"The tool {tool!r} isn't in this connection's allowed tools. An admin can add it.")
    if arguments is not None and not isinstance(arguments, dict):
        raise MCPError("arguments must be an object, e.g. {\"query\": \"mugs\"}")

    session = Session(config.get("server_url"), secrets.get("token"))
    session.start()
    if read_only:
        found = {t.get("name"): t for t in session.list_tools()}
        if tool not in found:
            raise MCPError(f"The MCP server has no tool named {tool!r}.")
        if not (found[tool].get("annotations") or {}).get("readOnlyHint"):
            raise MCPError(f"{tool!r} may change things, so it can't run as a read. Use the 'Use an MCP tool' step "
                           "instead (it asks for approval).")

    result = session.call_tool(tool, arguments)
    text = "\n".join(
        part.get("text", "") for part in result.get("content") or [] if isinstance(part, dict) and part.get("type") == "text"
    )[:MAX_RESULT_CHARS]
    if result.get("isError"):
        raise MCPError(f"The tool reported an error: {text or 'no details'}")
    return {"tool": tool, "text": text, "data": result.get("structuredContent")}
