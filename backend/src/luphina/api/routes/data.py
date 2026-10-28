"""
Data ownership: customers can take their data with them, delete a
workspace, or close their account.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import delete, func, select

from luphina import __version__, audit
from luphina.accounts import service as accounts
from luphina.accounts.security import verify_password
from luphina.api.deps import CurrentUser, Session, require_role
from luphina.engine import service as engine
from luphina.storage.models import (
    Approval,
    Connection,
    Customer,
    Invoice,
    Membership,
    User,
    Workflow,
    WorkflowExecution,
    Workspace,
)


router = APIRouter(tags=["data"])
OwnerAccess = Annotated[Membership, Depends(require_role("owner"))]

EXPORT_EXECUTION_LIMIT = 10_000


class DeleteWorkspace(BaseModel):
    confirm_name: str


class DeleteAccount(BaseModel):
    password: str


def _row(obj, exclude=()):
    return {
        column.key: getattr(obj, column.key)
        for column in obj.__table__.columns
        if column.key not in exclude
    }


@router.get("/workspaces/{workspace_id}/export")
def export_workspace(membership: OwnerAccess, session: Session):
    """Everything the workspace owns, as one JSON file. Secrets are never exported."""

    workspace_id = membership.workspace_id
    scoped = lambda model: session.scalars(select(model).where(model.workspace_id == workspace_id)).all()  # noqa: E731

    executions = session.scalars(
        select(WorkflowExecution)
        .where(WorkflowExecution.workspace_id == workspace_id)
        .order_by(WorkflowExecution.id.desc())
        .limit(EXPORT_EXECUTION_LIMIT)
    ).all()

    document = {
        "format": "luphina-export-v1",
        "exported_at": datetime.now(timezone.utc),
        "luphina_version": __version__,
        "workspace": _row(session.get(Workspace, workspace_id)),
        "members": [
            {"email": m.user.email, "name": m.user.name, "role": m.role}
            for m in accounts.list_workspace_members(session, workspace_id)
        ],
        "workflows": [
            {**_row(w), "versions": [_row(v) for v in w.versions]} for w in scoped(Workflow)
        ],
        "executions": [
            {**_row(e), "steps": [_row(s) for s in e.steps]} for e in executions
        ],
        "customers": [_row(c) for c in scoped(Customer)],
        "approvals": [_row(a) for a in scoped(Approval)],
        "connections": [_row(c, exclude=("encrypted_secrets",)) for c in scoped(Connection)],
        "invoices": [_row(i) for i in scoped(Invoice)],
    }

    filename = f"luphina-{membership.workspace.slug}-{datetime.now(timezone.utc):%Y%m%d}.json"
    audit.for_member(membership, session, "data.exported")
    return JSONResponse(
        jsonable_encoder(document),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _delete_workspace(session, workspace_id):
    # Stop anything in flight before the data disappears
    engine.emergency_stop(session, workspace_id, reason="Workspace deleted")
    # Database cascades remove workflows, runs, customers, connections, ...
    session.execute(delete(Workspace).where(Workspace.id == workspace_id))
    session.commit()


@router.delete("/workspaces/{workspace_id}", status_code=204)
def delete_workspace(request: DeleteWorkspace, membership: OwnerAccess, session: Session):
    if request.confirm_name.strip() != membership.workspace.name:
        raise HTTPException(status_code=409, detail="Type the workspace name exactly to confirm.")

    _delete_workspace(session, membership.workspace_id)
    # Account-level record: the workspace's own events are deleted with it
    audit.record(session, "workspace.deleted", user_id=membership.user_id,
                 target=request.confirm_name, details={"workspace_id": membership.workspace_id})


@router.delete("/me", status_code=204)
def delete_account(request: DeleteAccount, user: CurrentUser, session: Session):
    """Close the account. Workspaces only this user belongs to are deleted."""

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=403, detail="Incorrect password.")

    memberships = accounts.list_user_memberships(session, user.id)
    to_delete = []

    for membership in memberships:
        members = session.scalar(
            select(func.count(Membership.id)).where(Membership.workspace_id == membership.workspace_id)
        )
        owners = session.scalar(
            select(func.count(Membership.id)).where(
                Membership.workspace_id == membership.workspace_id, Membership.role == "owner"
            )
        )

        if members == 1:
            to_delete.append(membership.workspace_id)
        elif membership.role == "owner" and owners == 1:
            raise HTTPException(
                status_code=409,
                detail=f"You are the only owner of “{membership.workspace.name}”. Make someone else owner first.",
            )

    for workspace_id in to_delete:
        _delete_workspace(session, workspace_id)

    audit.record(session, "account.deleted", user_id=user.id, target=user.email)
    session.execute(delete(User).where(User.id == user.id))
    session.commit()
