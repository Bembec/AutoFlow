"""Workflow engine API: workflows, versions, executions and the action catalogue."""

from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, Response, UploadFile
from starlette.concurrency import run_in_threadpool

from luphina import audit, documents
from luphina.ai import builder, providers
from luphina.api import schemas
from luphina.api.deps import MemberAccess, Session, ViewerAccess
from luphina.engine import diff, executor, limits
from luphina.engine import service as engine
from luphina.engine.actions import describe_actions
from luphina.engine.definition import WorkflowDefinition
from luphina.engine.templates import TEMPLATES


router = APIRouter(tags=["workflows"])
workspace_router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["workflows"])

ExecutionStatus = Literal[
    "queued", "running", "waiting_approval", "succeeded",
    "failed", "cancelled", "needs_attention",
]


def _errors(action):
    try:
        return action()
    except engine.NotFound:
        raise HTTPException(status_code=404, detail="Not found")
    except (engine.WorkflowError, executor.ExecutionConflict) as error:
        raise HTTPException(status_code=409, detail=str(error))
    except ValueError as error:
        # A stored definition no longer validates (e.g. an action was removed)
        raise HTTPException(status_code=422, detail=str(error))


@router.get("/actions")
def list_actions():
    """Every action a workflow step can use."""
    return describe_actions()


@router.get("/templates")
def list_templates():
    return [
        {
            "slug": t["slug"],
            "name": t["name"],
            "description": t["description"],
            "category": t.get("category", "General"),
            "requires": t.get("requires", []),
            # Needs this feature flag switched on (e.g. smarter_logic); None = always available
            "feature": t.get("feature"),
        }
        for t in TEMPLATES.values()
    ]


@workspace_router.get("/workflows", response_model=list[schemas.WorkflowOut])
def list_workflows(
    membership: ViewerAccess, session: Session, include_archived: bool = False
):
    return engine.list_workflows(session, membership.workspace_id, include_archived)


def _require_features(session, membership, definition):
    """Workflows using optional features need them switched on for the workspace."""
    from luphina import features
    from luphina.engine.definition import required_features
    from luphina.engine.limits import get_workspace

    if definition is None:
        return
    workspace = get_workspace(session, membership.workspace_id)
    missing = sorted(name for name in required_features(definition) if not features.enabled(name, workspace))
    messages = {
        "smarter_logic": "Comparisons, AND/OR conditions and loops are not switched on for this workspace yet.",
        "mcp_tools": "MCP tools are not switched on for this workspace yet.",
        "ai_assistants": "AI assistants are not switched on for this workspace yet.",
    }
    if missing:
        raise HTTPException(status_code=403, detail=" ".join(messages[name] for name in missing))


@workspace_router.post("/workflows", response_model=schemas.WorkflowOut, status_code=201)
def create_workflow(request: schemas.WorkflowCreate, membership: MemberAccess, session: Session):
    _require_features(session, membership, request.definition)
    return _errors(lambda: engine.create_workflow(
        session,
        membership.workspace_id,
        request.name,
        request.definition,
        request.description,
        user_id=membership.user_id,
        minutes_saved_per_run=request.minutes_saved_per_run,
    ))


@workspace_router.post(
    "/workflows/from-template", response_model=schemas.WorkflowOut, status_code=201
)
def create_from_template(
    request: schemas.WorkflowFromTemplate, membership: MemberAccess, session: Session
):
    template = TEMPLATES.get(request.template)

    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    _require_features(session, membership, WorkflowDefinition.model_validate(template["definition"]))

    return _errors(lambda: engine.create_workflow(
        session,
        membership.workspace_id,
        request.name or template["name"],
        template["definition"],
        template["description"],
        user_id=membership.user_id,
        source_template=request.template,
    ))


@workspace_router.post("/workflows/ai-draft", response_model=schemas.AIDraftOut)
def ai_draft(request: schemas.AIDraftRequest, membership: MemberAccess, session: Session):
    """Describe a process in plain words; get a validated workflow draft."""

    from luphina import features
    from luphina.engine.limits import get_workspace

    if not features.enabled("ai_builder", get_workspace(session, membership.workspace_id)):
        raise HTTPException(status_code=403, detail="The AI builder is switched off for this workspace. Start from a template instead.")

    try:
        draft = builder.draft_workflow(
            request.request, [answer.model_dump() for answer in request.answers]
        )
    except providers.AIUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error))
    except builder.DraftFailed as error:
        raise HTTPException(status_code=422, detail=str(error))

    workflow = None

    if request.save and draft.definition is not None:
        _require_features(session, membership, WorkflowDefinition.model_validate(draft.definition))
        workflow = _errors(lambda: engine.create_workflow(
            session,
            membership.workspace_id,
            draft.name,
            draft.definition,
            draft.description,
            user_id=membership.user_id,
        ))

    return {
        "status": draft.status,
        "name": draft.name,
        "description": draft.description,
        "definition": draft.definition,
        "questions": draft.questions,
        "assumptions": draft.assumptions,
        "unsupported": draft.unsupported,
        "provider": draft.provider,
        "attempts": draft.attempts,
        "workflow": workflow,
    }


@workspace_router.get("/workflows/{workflow_id}", response_model=schemas.WorkflowOut)
def get_workflow(workflow_id: int, membership: ViewerAccess, session: Session):
    return _errors(lambda: engine.get_workflow(session, membership.workspace_id, workflow_id))


@workspace_router.patch("/workflows/{workflow_id}", response_model=schemas.WorkflowOut)
def update_workflow(
    workflow_id: int,
    request: schemas.WorkflowUpdate,
    membership: MemberAccess,
    session: Session,
):
    _require_features(session, membership, request.definition)
    return _errors(lambda: engine.update_workflow(
        session,
        membership.workspace_id,
        workflow_id,
        request.name,
        request.description,
        request.definition,
        request.minutes_saved_per_run,
        request.mcp_enabled,
    ))


@workspace_router.post("/workflows/{workflow_id}/publish", response_model=schemas.WorkflowOut)
def publish_workflow(
    workflow_id: int,
    membership: MemberAccess,
    session: Session,
    request: schemas.PublishRequest | None = None,
):
    version = request.version if request else None
    before = _errors(lambda: engine.get_workflow(session, membership.workspace_id, workflow_id))
    live = engine.version_in_state(before, "published")
    target = (
        next((v for v in before.versions if v.number == version), None) if version
        else engine.version_in_state(before, "draft")
    )
    # What this publish changes, recorded for the activity log
    changes = diff.compare(live.definition, target.definition) if live and target else []

    workflow = _errors(lambda: engine.publish(session, membership.workspace_id, workflow_id, version))
    audit.for_member(membership, session, "workflow.published", target=workflow.name, details={
        "version": version,
        "changes": len(changes),
        "steps_changed": sorted({c["step_id"] for c in changes if "step_id" in c}),
    })
    return workflow


@workspace_router.get("/workflows/{workflow_id}/compare")
def compare_versions(
    workflow_id: int,
    membership: ViewerAccess,
    session: Session,
    before: int | None = None,
    after: int | None = None,
):
    """What changes between two versions (default: the live version → the draft)."""
    workflow = _errors(lambda: engine.get_workflow(session, membership.workspace_id, workflow_id))
    by_number = {v.number: v for v in workflow.versions}

    old = by_number.get(before) if before else engine.version_in_state(workflow, "published")
    new = by_number.get(after) if after else engine.version_in_state(workflow, "draft")
    if (before and old is None) or (after and new is None):
        raise HTTPException(status_code=404, detail="Version not found")
    if old is None or new is None:
        return {"before": old.number if old else None, "after": new.number if new else None, "changes": []}
    return {"before": old.number, "after": new.number, "changes": diff.compare(old.definition, new.definition)}


@workspace_router.post("/workflows/{workflow_id}/pause", response_model=schemas.WorkflowOut)
def pause_workflow(workflow_id: int, membership: MemberAccess, session: Session):
    """Emergency stop for one workflow: cancels its open runs."""
    workflow = _errors(lambda: engine.pause(session, membership.workspace_id, workflow_id))
    audit.for_member(membership, session, "workflow.paused", target=workflow.name)
    return workflow


@workspace_router.post("/workflows/{workflow_id}/resume", response_model=schemas.WorkflowOut)
def resume_workflow(workflow_id: int, membership: MemberAccess, session: Session):
    workflow = _errors(lambda: engine.resume(session, membership.workspace_id, workflow_id))
    audit.for_member(membership, session, "workflow.resumed", target=workflow.name)
    return workflow


@workspace_router.post("/workflows/{workflow_id}/archive", response_model=schemas.WorkflowOut)
def archive_workflow(workflow_id: int, membership: MemberAccess, session: Session):
    workflow = _errors(lambda: engine.archive(session, membership.workspace_id, workflow_id))
    audit.for_member(membership, session, "workflow.archived", target=workflow.name)
    return workflow


@workspace_router.post(
    "/workflows/{workflow_id}/executions",
    response_model=schemas.ExecutionOut,
    status_code=201,
)
def start_execution(
    workflow_id: int,
    membership: MemberAccess,
    session: Session,
    response: Response,
    request: schemas.ExecutionStart | None = None,
    idempotency_key: Annotated[str | None, Header(max_length=200)] = None,
):
    request = request or schemas.ExecutionStart()

    execution, created = _errors(lambda: engine.start_execution(
        session,
        membership.workspace_id,
        workflow_id,
        mode=request.mode,
        payload=request.payload,
        idempotency_key=idempotency_key,
        user_id=membership.user_id,
    ))

    if not created:
        # Same Idempotency-Key as an earlier request: nothing new was started
        response.status_code = 200

    return execution


@workspace_router.post(
    "/workflows/{workflow_id}/documents",
    response_model=schemas.ExecutionOut,
    status_code=201,
)
async def run_with_document(
    workflow_id: int,
    membership: MemberAccess,
    session: Session,
    file: Annotated[UploadFile, File(description="PDF, image or text file (max 10 MB)")],
    mode: Annotated[Literal["test", "live"], Form()] = "live",
):
    """Start a run with an uploaded document; its text becomes the trigger data."""

    data = await file.read(documents.MAX_BYTES + 1)

    def count_ai():
        # Reading a scan or photo is an AI call: it counts toward the daily limit
        try:
            limits.use_ai_call(session, limits.get_workspace(session, membership.workspace_id), "ocr")
        except limits.LimitReached as error:
            raise documents.DocumentError(str(error)) from error

    workflow = _errors(lambda: engine.get_workflow(session, membership.workspace_id, workflow_id))
    if mode == "live":
        published = engine.version_in_state(workflow, "published")
        trigger_type = published.definition.get("trigger", {}).get("type") if published else None
        if trigger_type != "document":
            raise HTTPException(status_code=409, detail="Live document runs need a published workflow with a document trigger.")

    try:
        # Reading the file can involve an AI call (OCR), so run it off the event loop
        payload = await run_in_threadpool(
            documents.extract_text, data, file.filename or "document", True, count_ai
        )
    except documents.DocumentError as error:
        raise HTTPException(status_code=422, detail=str(error))

    execution, _ = _errors(lambda: engine.start_execution(
        session,
        membership.workspace_id,
        workflow_id,
        mode=mode,
        payload=payload,
        user_id=membership.user_id,
    ))
    return execution


@workspace_router.get("/executions", response_model=list[schemas.ExecutionOut])
def list_executions(
    membership: ViewerAccess,
    session: Session,
    workflow_id: int | None = None,
    status: ExecutionStatus | None = None,
    limit: int = Query(20, ge=1, le=100),
):
    return engine.list_executions(session, membership.workspace_id, workflow_id, status, limit)


@workspace_router.get("/executions/{execution_id}", response_model=schemas.ExecutionOut)
def get_execution(execution_id: int, membership: ViewerAccess, session: Session):
    return _errors(lambda: engine.get_execution(session, membership.workspace_id, execution_id))


@workspace_router.post("/executions/{execution_id}/cancel", response_model=schemas.ExecutionOut)
def cancel_execution(execution_id: int, membership: MemberAccess, session: Session):
    return _errors(lambda: executor.cancel(
        session, engine.get_execution(session, membership.workspace_id, execution_id)
    ))


@workspace_router.post("/executions/{execution_id}/confirm-done", response_model=schemas.ExecutionOut)
def confirm_execution_step_done(execution_id: int, membership: MemberAccess, session: Session):
    """The uncertain step did happen (e.g. the email arrived): continue after it."""
    return _errors(lambda: executor.confirm_completed(
        session, engine.get_execution(session, membership.workspace_id, execution_id)
    ))


@workspace_router.post("/executions/{execution_id}/retry", response_model=schemas.ExecutionOut)
def retry_execution(
    execution_id: int,
    membership: MemberAccess,
    session: Session,
    request: schemas.ExecutionRetry | None = None,
):
    confirm = request.confirm_not_completed if request else False

    return _errors(lambda: executor.retry(
        session,
        engine.get_execution(session, membership.workspace_id, execution_id),
        confirm_not_completed=confirm,
    ))
