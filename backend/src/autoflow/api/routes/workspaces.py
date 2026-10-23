"""Workspaces and their members."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from autoflow import audit, notifications
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


class RoleChange(BaseModel):
    role: schemas.Role


@router.patch("/workspaces/{workspace_id}/members/{user_id}", response_model=schemas.MemberOut)
def change_member_role(user_id: int, request: RoleChange, membership: AdminAccess, session: Session):
    try:
        changed = accounts.change_role(session, membership, user_id, request.role)
    except accounts.AccountError as error:
        raise HTTPException(status_code=409, detail=str(error))

    session.commit()
    audit.for_member(membership, session, "member.role_changed", target=changed.user.email, details={"role": changed.role})
    return _member_out(changed)


@router.delete("/workspaces/{workspace_id}/members/{user_id}", status_code=204)
def remove_member(user_id: int, membership: AdminAccess, session: Session):
    try:
        accounts.remove_member(session, membership, user_id)
    except accounts.AccountError as error:
        raise HTTPException(status_code=409, detail=str(error))

    session.commit()
    audit.for_member(membership, session, "member.removed", target=f"user {user_id}")


class NotificationSettings(BaseModel):
    notify_email: EmailStr | None = None
    notify_smtp_connection: str | None = Field(None, max_length=100)
    notify_slack_connection: str | None = Field(None, max_length=100)
    notify_on_approval: bool | None = None
    notify_on_failure: bool | None = None


NOTIFICATION_FIELDS = (
    "notify_email", "notify_smtp_connection", "notify_slack_connection", "notify_on_approval", "notify_on_failure",
)


@router.get("/workspaces/{workspace_id}/notifications")
def get_notification_settings(membership: ViewerAccess, session: Session):
    workspace = limits.get_workspace(session, membership.workspace_id)
    return {field: getattr(workspace, field) for field in NOTIFICATION_FIELDS}


@router.patch("/workspaces/{workspace_id}/notifications")
def update_notification_settings(request: NotificationSettings, membership: AdminAccess, session: Session):
    workspace = limits.get_workspace(session, membership.workspace_id)
    for field, value in request.model_dump(exclude_unset=True).items():
        if field in ("notify_on_approval", "notify_on_failure") and value is None:
            continue
        setattr(workspace, field, value or None if isinstance(value, str) else value)
    session.commit()
    audit.for_member(membership, session, "settings.notifications_changed")
    return {field: getattr(workspace, field) for field in NOTIFICATION_FIELDS}


@router.post("/workspaces/{workspace_id}/notifications/test", status_code=202)
def send_test_notification(membership: AdminAccess, session: Session):
    queued = notifications.enqueue(
        session,
        membership.workspace_id,
        "test",
        "Test notification",
        "Notifications are set up. You will hear from AutoFlow when something needs you.",
        link="/dashboard",
    )
    if queued is None:
        raise HTTPException(status_code=409, detail="Set an email (with a mailbox connection) or a Slack connection first.")
    session.commit()
    return {"queued": True, "note": "The background worker sends it within a few seconds."}


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
    audit.for_member(membership, session, "settings.policies_changed", details=request.model_dump(exclude_none=True))
    return _policies_out(session, workspace)


@router.post("/workspaces/{workspace_id}/emergency-stop")
def emergency_stop(membership: AdminAccess, session: Session, request: EmergencyStop | None = None):
    """Stop every automation in the workspace and cancel open runs."""

    stopped = engine.emergency_stop(
        session, membership.workspace_id, request.reason if request else None
    )
    audit.for_member(membership, session, "automation.emergency_stop", details={"reason": request.reason if request else None, "cancelled": stopped})
    return {"automation_paused": True, "executions_cancelled": stopped}


@router.post("/workspaces/{workspace_id}/resume-automations")
def resume_automations(membership: AdminAccess, session: Session):
    workspace = limits.get_workspace(session, membership.workspace_id)
    if workspace.staff_suspended_reason:
        raise HTTPException(
            status_code=403,
            detail=f"AutoFlow staff paused this workspace: {workspace.staff_suspended_reason} Contact support to resolve it.",
        )
    engine.resume_automations(session, membership.workspace_id)
    audit.for_member(membership, session, "automation.resumed")
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
    audit.for_member(membership, session, "member.added", target=new_membership.user.email, details={"role": new_membership.role})
    return _member_out(new_membership)


def _audit_out(event, emails):
    return {
        "id": event.id,
        "action": event.action,
        "user": emails.get(event.user_id),
        "target": event.target,
        "details": event.details,
        "ip": event.ip,
        "created_at": event.created_at,
    }


@router.get("/workspaces/{workspace_id}/audit")
def audit_log(membership: AdminAccess, session: Session, before_id: int | None = None):
    """Who did what in this workspace (newest first, 200 per page)."""

    events = audit.list_events(session, membership.workspace_id, before_id=before_id)
    emails = {m.user.id: m.user.email for m in accounts.list_workspace_members(session, membership.workspace_id)}
    return [_audit_out(event, emails) for event in events]
