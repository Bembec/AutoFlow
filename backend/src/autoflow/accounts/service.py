"""
Accounts, workspaces and memberships.

A user can belong to several workspaces, each with one role:
viewer < member < admin < owner.
"""

import re
import secrets
from datetime import timedelta

from sqlalchemy import select

from autoflow import config
from autoflow.accounts.security import (
    hash_password,
    hash_token,
    new_access_token,
    verify_password,
)
from autoflow.storage.db import utc_now
from autoflow.storage.models import (
    ROLES,
    AccessToken,
    Membership,
    User,
    Workspace,
)


class AccountError(Exception):
    """A request about accounts that cannot be completed."""


def role_at_least(role, minimum_role):
    return ROLES.index(role) >= ROLES.index(minimum_role)


def _unique_slug(session, name):
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:50] or "workspace"
    slug = base

    while session.scalar(select(Workspace).where(Workspace.slug == slug)):
        slug = f"{base}-{secrets.token_hex(3)}"

    return slug


def get_user_by_email(session, email):
    return session.scalar(select(User).where(User.email == email.strip().lower()))


def register_user(session, email, name, password):
    """Create a user together with their own workspace (as owner)."""

    if get_user_by_email(session, email) is not None:
        raise AccountError("An account with this email already exists.")

    user = User(
        email=email.strip().lower(),
        name=name.strip(),
        password_hash=hash_password(password),
    )
    session.add(user)
    session.flush()

    create_workspace(session, user, f"{user.name}'s workspace")
    return user


def authenticate(session, email, password):
    """Return a new access token for valid credentials, else None."""

    user = get_user_by_email(session, email)

    # Same response for unknown email and wrong password
    if user is None or not verify_password(password, user.password_hash):
        return None

    token, token_hash = new_access_token()
    session.add(
        AccessToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=utc_now() + timedelta(hours=config.ACCESS_TOKEN_TTL_HOURS),
        )
    )
    session.flush()
    return token


def user_for_token(session, token):
    """Return the user for a valid, unexpired, unrevoked token."""

    access_token = session.scalar(
        select(AccessToken).where(AccessToken.token_hash == hash_token(token))
    )

    if (
        access_token is None
        or access_token.revoked_at is not None
        or access_token.expires_at <= utc_now()
    ):
        return None

    return access_token.user


def revoke_token(session, token):
    access_token = session.scalar(
        select(AccessToken).where(AccessToken.token_hash == hash_token(token))
    )

    if access_token is not None and access_token.revoked_at is None:
        access_token.revoked_at = utc_now()
        session.flush()


def create_workspace(session, owner, name):
    workspace = Workspace(name=name.strip(), slug=_unique_slug(session, name))
    session.add(workspace)
    session.flush()

    session.add(Membership(user_id=owner.id, workspace_id=workspace.id, role="owner"))
    session.flush()
    return workspace


def get_membership(session, user_id, workspace_id):
    return session.scalar(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.workspace_id == workspace_id,
        )
    )


def list_user_memberships(session, user_id):
    return session.scalars(
        select(Membership)
        .where(Membership.user_id == user_id)
        .order_by(Membership.workspace_id)
    ).all()


def list_workspace_members(session, workspace_id):
    return session.scalars(
        select(Membership)
        .where(Membership.workspace_id == workspace_id)
        .order_by(Membership.id)
    ).all()


def add_member(session, acting_membership, email, role):
    """Add an existing user to the acting member's workspace."""

    if role not in ROLES:
        raise AccountError(f"Unknown role: {role}")

    # Nobody can grant a role above their own
    if not role_at_least(acting_membership.role, role):
        raise AccountError("You cannot grant a role higher than your own.")

    user = get_user_by_email(session, email)

    if user is None:
        raise AccountError("No account exists with this email.")

    if get_membership(session, user.id, acting_membership.workspace_id):
        raise AccountError("This user is already a member.")

    from autoflow.billing.service import PlanLimitReached, check_can_add_member

    try:
        check_can_add_member(session, acting_membership.workspace_id)
    except PlanLimitReached as limit:
        raise AccountError(str(limit)) from limit

    membership = Membership(
        user_id=user.id,
        workspace_id=acting_membership.workspace_id,
        role=role,
    )
    session.add(membership)
    session.flush()
    return membership


def ensure_local_workspace(session):
    """Return the workspace used by the command-line workflow."""

    workspace = session.scalar(
        select(Workspace).where(Workspace.slug == config.LOCAL_WORKSPACE_SLUG)
    )

    if workspace is None:
        workspace = Workspace(name="Local workspace", slug=config.LOCAL_WORKSPACE_SLUG)
        session.add(workspace)
        session.flush()

    return workspace
