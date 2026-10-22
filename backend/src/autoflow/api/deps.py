"""
Shared API dependencies: database session, current user and
workspace access checks.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session as OrmSession

from autoflow.accounts import service as accounts
from autoflow.storage.db import SessionFactory
from autoflow.storage.models import Membership, User


bearer_scheme = HTTPBearer(auto_error=False)


def get_session():
    session = SessionFactory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


Session = Annotated[OrmSession, Depends(get_session)]


def get_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def get_current_user(session: Session, token: Annotated[str, Depends(get_token)]):
    user = accounts.user_for_token(session, token)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(minimum_role):
    """Dependency factory: the caller must have at least this role."""

    def dependency(
        session: Session,
        user: CurrentUser,
        workspace_id: Annotated[int, Path()],
    ):
        membership = accounts.get_membership(session, user.id, workspace_id)

        # Answer 404, not 403, so other workspaces' ids are not revealed
        if membership is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        if not accounts.role_at_least(membership.role, minimum_role):
            raise HTTPException(
                status_code=403,
                detail=f"This action needs the {minimum_role} role or higher.",
            )

        return membership

    return dependency


ViewerAccess = Annotated[Membership, Depends(require_role("viewer"))]
MemberAccess = Annotated[Membership, Depends(require_role("member"))]
AdminAccess = Annotated[Membership, Depends(require_role("admin"))]
