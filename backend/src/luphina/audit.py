"""
Audit log: who did what, and when.

Security-relevant actions (sign-ins, team and role changes, connected
apps, publishing, emergency stops, approvals, exports) are recorded with
the acting user. Secrets are never put in the details.
"""

from sqlalchemy import select

from luphina.storage.models import AuditEvent


def record(session, action, *, workspace_id=None, user_id=None, target=None, details=None, ip=None):
    """Add an audit event and commit it."""

    session.add(AuditEvent(
        workspace_id=workspace_id,
        user_id=user_id,
        action=action,
        target=str(target)[:200] if target is not None else None,
        details=details,
        ip=ip,
    ))
    session.commit()


def for_member(membership, session, action, target=None, details=None):
    """Shortcut for actions done by a workspace member."""

    record(
        session,
        action,
        workspace_id=membership.workspace_id,
        user_id=membership.user_id,
        target=target,
        details=details,
    )


def list_events(session, workspace_id, limit=200, before_id=None):
    query = select(AuditEvent).where(AuditEvent.workspace_id == workspace_id)
    if before_id:
        query = query.where(AuditEvent.id < before_id)
    return session.scalars(query.order_by(AuditEvent.id.desc()).limit(limit)).all()
