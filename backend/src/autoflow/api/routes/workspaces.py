"""Workspaces and their members."""

from fastapi import APIRouter, HTTPException, status

from autoflow.accounts import service as accounts
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
