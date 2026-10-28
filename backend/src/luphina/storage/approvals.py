"""
Human-approval requests, always scoped to one workspace.

An approval is created when Luphina needs a human decision (an AI
classification or an outgoing email) and nobody is at the terminal.
At most one *pending* approval exists per workspace, kind and email.
"""

from sqlalchemy import select, update

from luphina.storage.db import utc_now
from luphina.storage.models import Approval


APPROVAL_KINDS = ("classification", "email")


def upsert_pending_approval(session, workspace_id, kind, customer_email, payload):
    """Create a pending approval, or refresh the existing pending one."""

    if kind not in APPROVAL_KINDS:
        raise ValueError(f"Unknown approval kind: {kind}")

    customer_email = customer_email.strip().lower()
    pending = list_approvals(session, workspace_id, "pending", kind, customer_email)

    if pending:
        pending[0].payload = payload
        pending[0].created_at = utc_now()
        approval = pending[0]
    else:
        approval = Approval(
            workspace_id=workspace_id,
            kind=kind,
            customer_email=customer_email,
            payload=payload,
        )
        session.add(approval)

    session.flush()
    return approval


def list_approvals(session, workspace_id, status=None, kind=None, customer_email=None):
    """Return approvals, newest first, optionally filtered."""

    query = select(Approval).where(Approval.workspace_id == workspace_id)

    if status is not None:
        query = query.where(Approval.status == status)
    if kind is not None:
        query = query.where(Approval.kind == kind)
    if customer_email is not None:
        query = query.where(Approval.customer_email == customer_email)

    return session.scalars(query.order_by(Approval.id.desc())).all()


def get_approval(session, workspace_id, approval_id):
    # populate_existing: always read the latest status from the database
    return session.scalar(
        select(Approval)
        .where(
            Approval.workspace_id == workspace_id,
            Approval.id == approval_id,
        )
        .execution_options(populate_existing=True)
    )


def claim_pending_approval(session, workspace_id, approval_id, status, decision, user_id=None):
    """Atomically move a pending approval to a final status.

    Returns True only for the caller that made the change, so the same
    approval can never be acted on twice.
    """

    result = session.execute(
        update(Approval)
        .where(
            Approval.workspace_id == workspace_id,
            Approval.id == approval_id,
            Approval.status == "pending",
        )
        .values(
            status=status,
            decision=decision,
            decided_by_user_id=user_id,
            decided_at=utc_now(),
        )
        .execution_options(synchronize_session=False)
    )

    # Commit the claim before acting on it, so a crash or retry
    # afterwards can never repeat the action
    session.commit()
    return result.rowcount == 1


def set_approval_status(session, workspace_id, approval_id, status):
    """Record the final outcome after an approved action ran."""

    session.execute(
        update(Approval)
        .where(Approval.workspace_id == workspace_id, Approval.id == approval_id)
        .values(status=status)
        .execution_options(synchronize_session=False)
    )
    session.commit()
