"""
Luphina as an MCP server: outside AI assistants can run workflows and check runs.

Streamable HTTP transport, JSON replies (no server-sent events needed):
POST /mcp with one JSON-RPC message. Authenticated by a workspace API key
(Authorization: Bearer afk_...), created by an admin under Settings.

Tools offered:
- run_<workflow>: one per workflow an admin opted in ("Let AI assistants
  run this workflow"). Runs follow every normal rule: approvals, limits,
  the email safety check, the activity log. An optional idempotency_key
  makes a repeated call return the same run instead of starting another.
- list_recent_runs, get_run: read-only, only for opted-in workflows.
"""

import re
import secrets
from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from autoflow import __version__, audit, config, features
from autoflow.accounts.security import hash_token
from autoflow.api.deps import AdminAccess, Session
from autoflow.engine import limits
from autoflow.engine import service as engine
from autoflow.storage.db import utc_now
from autoflow.storage.models import ApiKey, AuditEvent, Workflow, WorkflowExecution

router = APIRouter(tags=["mcp server"])

SUPPORTED_VERSIONS = ("2025-06-18", "2025-03-26")
CALLS_PER_HOUR = 60
KEY_PREFIX = "afk_"


# --- API keys (Settings) ---------------------------------------------------------

class KeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


def _key_out(key):
    return {"id": key.id, "name": key.name, "prefix": key.prefix, "created_at": key.created_at,
            "last_used_at": key.last_used_at, "revoked": key.revoked_at is not None}


@router.get("/workspaces/{workspace_id}/api-keys")
def list_keys(membership: AdminAccess, session: Session):
    keys = session.scalars(select(ApiKey).where(ApiKey.workspace_id == membership.workspace_id)
                           .order_by(ApiKey.id.desc())).all()
    return {"server_url": f"{config.PUBLIC_URL}/mcp", "keys": [_key_out(key) for key in keys]}


@router.post("/workspaces/{workspace_id}/api-keys", status_code=201)
def create_key(request: KeyCreate, membership: AdminAccess, session: Session):
    if not features.enabled("mcp_server", membership.workspace):
        raise HTTPException(status_code=403, detail="Access for AI assistants is not switched on for this workspace yet.")
    secret = KEY_PREFIX + secrets.token_urlsafe(32)
    key = ApiKey(workspace_id=membership.workspace_id, name=request.name.strip(), prefix=secret[:12],
                 key_hash=hash_token(secret), created_by_user_id=membership.user_id)
    session.add(key)
    session.commit()
    audit.for_member(membership, session, "api_key.created", target=key.name)
    # The only time the full key is ever shown
    return {**_key_out(key), "key": secret}


@router.delete("/workspaces/{workspace_id}/api-keys/{key_id}", status_code=204)
def revoke_key(key_id: int, membership: AdminAccess, session: Session):
    key = session.get(ApiKey, key_id)
    if key is None or key.workspace_id != membership.workspace_id:
        raise HTTPException(status_code=404, detail="Key not found")
    if key.revoked_at is None:
        key.revoked_at = utc_now()
        session.commit()
        audit.for_member(membership, session, "api_key.revoked", target=key.name)


# --- the MCP endpoint ---------------------------------------------------------------

class ToolError(Exception):
    """Reported to the assistant as a tool result with isError, not a protocol error."""


def _authenticate(request, session):
    header = request.headers.get("Authorization", "")
    token = header[7:].strip() if header.lower().startswith("bearer ") else ""
    key = session.scalar(select(ApiKey).where(ApiKey.key_hash == hash_token(token))) if token else None
    if key is None or key.revoked_at is not None:
        raise HTTPException(status_code=401, detail="A valid Luphina API key is required.",
                            headers={"WWW-Authenticate": "Bearer"})
    workspace = limits.get_workspace(session, key.workspace_id)
    if not features.enabled("mcp_server", workspace):
        raise HTTPException(status_code=403, detail="Access for AI assistants is not switched on for this workspace.")
    key.last_used_at = utc_now()
    session.commit()
    return key, workspace


def _tool_name(workflow):
    slug = re.sub(r"[^a-z0-9]+", "_", workflow.name.lower()).strip("_")[:40] or "workflow"
    return f"run_{slug}_{workflow.id}"


def _schema_for(payload):
    def kind(value):
        return {bool: "boolean", int: "number", float: "number", str: "string", list: "array", dict: "object"}.get(
            type(value), "string")

    properties = {key: {"type": kind(value)} for key, value in (payload or {}).items()}
    properties["idempotency_key"] = {
        "type": "string",
        "description": "Optional. Send the same key again and you get the same run instead of a second one.",
    }
    return {"type": "object", "properties": properties, "additionalProperties": True}


def _enabled_workflows(session, workspace):
    workflows = session.scalars(select(Workflow).where(
        Workflow.workspace_id == workspace.id, Workflow.mcp_enabled.is_(True), Workflow.status == "active",
    )).all()
    return [w for w in workflows if engine.version_in_state(w, "published") is not None]


def _tools(session, workspace):
    tools = []
    for workflow in _enabled_workflows(session, workspace):
        published = engine.version_in_state(workflow, "published")
        tools.append({
            "name": _tool_name(workflow),
            "title": workflow.name,
            "description": (workflow.description or workflow.name)
            + " Runs the Luphina workflow; steps that need a person's approval wait for it.",
            "inputSchema": _schema_for(published.definition.get("trigger", {}).get("sample_payload")),
            "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False,
                            "openWorldHint": True},
        })
    tools += [
        {
            "name": "list_recent_runs",
            "title": "List recent runs",
            "description": "The latest runs of the workflows you may use, newest first.",
            "inputSchema": {"type": "object", "properties": {"limit": {"type": "number", "description": "1-20"}}},
            "annotations": {"readOnlyHint": True},
        },
        {
            "name": "get_run",
            "title": "Get a run",
            "description": "Status and steps of one run, by its number.",
            "inputSchema": {"type": "object", "properties": {"run_id": {"type": "number"}}, "required": ["run_id"]},
            "annotations": {"readOnlyHint": True},
        },
    ]
    return tools


def _run_summary(execution, names):
    return {
        "run_id": execution.id,
        "workflow": names.get(execution.workflow_id),
        "status": execution.status,
        "created_at": execution.created_at.isoformat(),
        "error": execution.error,
        "link": f"{config.PUBLIC_URL}/executions/{execution.id}",
    }


def _call(session, key, workspace, name, arguments):
    workflows = {w.id: w for w in _enabled_workflows(session, workspace)}
    names = {w.id: w.name for w in workflows.values()}

    if name == "list_recent_runs":
        limit = max(1, min(20, int(arguments.get("limit") or 10)))
        runs = session.scalars(select(WorkflowExecution).where(
            WorkflowExecution.workspace_id == workspace.id, WorkflowExecution.workflow_id.in_(list(workflows) or [0]),
        ).order_by(WorkflowExecution.id.desc()).limit(limit)).all()
        data = [_run_summary(run, names) for run in runs]
        return f"{len(data)} recent runs.", {"runs": data}

    if name == "get_run":
        try:
            run = engine.get_execution(session, workspace.id, int(arguments.get("run_id")))
        except (engine.NotFound, TypeError, ValueError):
            run = None
        if run is None or run.workflow_id not in workflows:
            raise ToolError("No run with that number among the workflows you may use.")
        data = {**_run_summary(run, names),
                "steps": [{"step": s.step_id, "status": s.status, "error": s.error} for s in run.steps]}
        return f"Run #{run.id}: {run.status}.", data

    workflow = next((w for w in workflows.values() if _tool_name(w) == name), None)
    if workflow is None:
        raise ToolError(f"Unknown tool {name!r}.")

    recent = session.scalar(select(func.count(AuditEvent.id)).where(
        AuditEvent.action == "mcp.run_workflow", AuditEvent.target == f"api_key:{key.id}",
        AuditEvent.created_at >= utc_now() - timedelta(hours=1),
    ))
    if recent >= CALLS_PER_HOUR:
        raise ToolError(f"This key may start at most {CALLS_PER_HOUR} runs an hour. Try again later.")

    payload = dict(arguments)
    supplied = str(payload.pop("idempotency_key", "") or "").strip()
    idempotency_key = f"mcp:{key.id}:{supplied}"[:200] if supplied else None
    try:
        execution, created = engine.start_execution(
            session, workspace.id, workflow.id, mode="live", payload=payload, idempotency_key=idempotency_key,
        )
    except engine.WorkflowError as error:
        raise ToolError(str(error)) from error
    if created:
        audit.record(session, "mcp.run_workflow", workspace_id=workspace.id, target=f"api_key:{key.id}",
                     details={"key": key.name, "workflow": workflow.name, "run": execution.id})

    note = {
        "waiting_approval": " It is waiting for a person to approve a step.",
        "failed": f" It failed: {execution.error}",
        "queued": " It is queued and will run shortly.",
    }.get(execution.status, "")
    text = f"{'Started' if created else 'Already started earlier:'} run #{execution.id} of {workflow.name}: {execution.status}.{note}"
    return text, _run_summary(execution, names)


def _reply(message_id, result=None, error=None):
    body = {"jsonrpc": "2.0", "id": message_id}
    body.update({"error": error} if error else {"result": result})
    return JSONResponse(body)


@router.get("/mcp", include_in_schema=False)
def mcp_get():
    # No server-initiated stream: replies come back on each POST
    return Response(status_code=405, headers={"Allow": "POST"})


@router.post("/mcp")
async def mcp_endpoint(request: Request, session: Session):
    key, workspace = _authenticate(request, session)
    try:
        message = await request.json()
    except ValueError:
        return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}},
                            status_code=400)
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid request"}},
                            status_code=400)

    method, message_id, params = message.get("method"), message.get("id"), message.get("params") or {}
    if message_id is None:
        # Notifications (e.g. notifications/initialized) need no answer
        return Response(status_code=202)

    if method == "initialize":
        asked = params.get("protocolVersion")
        return _reply(message_id, {
            "protocolVersion": asked if asked in SUPPORTED_VERSIONS else SUPPORTED_VERSIONS[0],
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "Luphina", "version": __version__},
            "instructions": (
                "Run this shop's Luphina workflows and check their runs. Runs follow the shop's rules: "
                "steps needing approval wait for a person, so report that instead of retrying."
            ),
        })
    if method == "ping":
        return _reply(message_id, {})
    if method == "tools/list":
        return _reply(message_id, {"tools": _tools(session, workspace)})
    if method == "tools/call":
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return _reply(message_id, error={"code": -32602, "message": "arguments must be an object"})
        try:
            text, data = _call(session, key, workspace, str(params.get("name") or ""), arguments)
        except ToolError as problem:
            return _reply(message_id, {"content": [{"type": "text", "text": str(problem)}], "isError": True})
        return _reply(message_id, {"content": [{"type": "text", "text": text}], "structuredContent": data,
                                   "isError": False})
    return _reply(message_id, error={"code": -32601, "message": f"Method not found: {method}"})
