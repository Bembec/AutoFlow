"""Workspaces and their members."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from autoflow.accounts import service as accounts
from autoflow.engine import limits
from autoflow.engine import service as engine
from autoflow.api import schemas
from autoflow.api.deps import AdminAccess, CurrentUser, Session, ViewerAccess


router = APIRouter(tags=["workspaces"])


def _member_out(membership):
    return {
        "user_id": membership.user.id,
        "email": membership.user.email,
        "name": membership.user.name,
        "role": membership.role,
    }


@router.post(
    "/workspaces",
    response_model=schemas.WorkspaceWithRole,
    status_code=status.HTTP_201_CREATED,
)
def create_workspace(request: schemas.WorkspaceCreate, user: CurrentUser, session: Session):
    workspace = accounts.create_workspace(session, user, request.name)
    session.commit()

    return {
        "id": workspace.id,
        "name": workspace.name,
        "slug": workspace.slug,
        "created_at": workspace.created_at,
        "role": "owner",
    }


@router.get("/workspaces/{workspace_id}/members", response_model=list[schemas.MemberOut])
def list_members(membership: ViewerAccess, session: Session):
    return [
        _member_out(member)
        for member in accounts.list_workspace_members(session, membership.workspace_id)
    ]


class EmergencyStop(BaseModel):
    reason: str | None = Field(None, max_length=500)


class PoliciesUpdate(BaseModel):
    approve_all_side_effects: bool | None = None
    max_executions_per_day: int | None = Field(None, ge=0, le=1_000_000)
    max_ai_calls_per_day: int | None = Field(None, ge=0, le=1_000_000)
    max_emails_per_day: int | None = Field(None, ge=0, le=1_000_000)


def _policies_out(session, workspace):
    return {
        "automation_paused": workspace.automation_paused,
        "paused_reason": workspace.paused_reason,
        "approve_all_side_effects": workspace.approve_all_side_effects,
        "max_executions_per_day": workspace.max_executions_per_day,
        "max_ai_calls_per_day": workspace.max_ai_calls_per_day,
        "max_emails_per_day": workspace.max_emails_per_day,
        "usage_today": limits.usage_today(session, workspace.id),
    }


@router.get("/workspaces/{workspace_id}/policies")
def get_policies(membership: ViewerAccess, session: Session):
    return _policies_out(session, limits.get_workspace(session, membership.workspace_id))


@router.patch("/workspaces/{workspace_id}/policies")
def update_policies(request: PoliciesUpdate, membership: AdminAccess, session: Session):
    workspace = limits.get_workspace(session, membership.workspace_id)

    for field, value in request.model_dump(exclude_none=True).items():
        setattr(workspace, field, value)

    session.commit()
    return _policies_out(session, workspace)


@router.post("/workspaces/{workspace_id}/emergency-stop")
def emergency_stop(membership: AdminAccess, session: Session, request: EmergencyStop | None = None):
    """Stop every automation in the workspace and cancel open runs."""

    stopped = engine.emergency_stop(
        session, membership.workspace_id, request.reason if request else None
    )
    return {"automation_paused": True, "executions_cancelled": stopped}


@router.post("/workspaces/{workspace_id}/resume-automations")
def resume_automations(membership: AdminAccess, session: Session):
    engine.resume_automations(session, membership.workspace_id)
    return {"automation_paused": False}


@router.post(
    "/workspaces/{workspace_id}/members",
    response_model=schemas.MemberOut,
    status_code=status.HTTP_201_CREATED,
)
def add_member(request: schemas.MemberCreate, membership: AdminAccess, session: Session):
    try:
        new_membership = accounts.add_member(
            session, membership, request.email, request.role
        )
    except accounts.AccountError as error:
        raise HTTPException(status_code=409, detail=str(error))

    session.commit()
    return _member_out(new_membership)
