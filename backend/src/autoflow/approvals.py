"""
Human-in-the-loop decisions for AutoFlow.

Sensitive actions (accepting an AI classification, emailing a customer)
wait as pending approvals until a person approves, corrects or rejects
them. Each approval can be decided exactly once, within one workspace.
"""

from autoflow.activity_log import timestamp_now, write_log_lines
from autoflow.emails.sender import send_email
from autoflow.emails.templates import create_email_preview
from autoflow.storage import approvals as approval_store
from autoflow.storage import customers as customer_store


CATEGORIES = ("Sales", "Support", "Other")


class ApprovalNotFound(Exception):
    """No approval exists with the requested id in this workspace."""


class ApprovalConflict(Exception):
    """The approval cannot be decided in its current state."""


def request_classification_review(session, workspace_id, customer, ai_result):
    """Queue an AI category suggestion for human review."""

    approval_store.upsert_pending_approval(
        session,
        workspace_id,
        "classification",
        customer["email"],
        {
            "name": customer["name"],
            "message": customer["message"],
            "suggested_category": ai_result["category"],
            "reason": ai_result["reason"],
        },
    )


def request_email_approval(session, workspace_id, email_preview):
    """Queue an outgoing email for human approval."""

    approval_store.upsert_pending_approval(
        session, workspace_id, "email", email_preview["to"], email_preview
    )


def _log_decision(approval, status):
    write_log_lines([
        f"{timestamp_now()} | APPROVAL | Workspace: {approval.workspace_id} | "
        f"{approval.kind.upper()} #{approval.id} {status.upper()} | "
        f"Email: {approval.customer_email}"
    ])


def _get_pending(session, workspace_id, approval_id):
    approval = approval_store.get_approval(session, workspace_id, approval_id)

    if approval is None:
        raise ApprovalNotFound(approval_id)

    if approval.status != "pending":
        raise ApprovalConflict(
            f"Approval {approval_id} is already {approval.status}."
        )

    return approval


def _claim(session, approval, status, decision, user_id):
    # Only one caller can move a pending approval forward
    if not approval_store.claim_pending_approval(
        session, approval.workspace_id, approval.id, status, decision, user_id
    ):
        raise ApprovalConflict(
            f"Approval {approval.id} was decided by someone else."
        )


def reject(session, workspace_id, approval_id, user_id=None):
    """Reject a pending approval; nothing is changed or sent."""

    approval = _get_pending(session, workspace_id, approval_id)
    _claim(session, approval, "rejected", {"approved": False}, user_id)
    _log_decision(approval, "rejected")

    if approval.kind == "step":
        _resume_execution(session, approval, approved=False)

    return approval_store.get_approval(session, workspace_id, approval_id)


def _resume_execution(session, approval, approved):
    # Imported here: the engine depends on storage, not on this module
    from autoflow.engine import executor
    from autoflow.engine.service import get_execution

    execution = get_execution(session, approval.workspace_id, approval.execution_id)
    executor.resume_after_decision(session, execution, approval.step_id, approved)


def approve(session, workspace_id, approval_id, category=None, user_id=None):
    """Approve a pending approval and carry out its action.

    For classifications, `category` optionally corrects the AI suggestion.
    """

    approval = _get_pending(session, workspace_id, approval_id)

    if approval.kind == "step":
        if category is not None:
            raise ApprovalConflict("A category only applies to classifications.")
        _claim(session, approval, "approved", {"approved": True}, user_id)
        _log_decision(approval, "approved")
        _resume_execution(session, approval, approved=True)
    elif approval.kind == "classification":
        _approve_classification(session, approval, category, user_id)
    else:
        if category is not None:
            raise ApprovalConflict("A category only applies to classifications.")
        _approve_email(session, approval, user_id)

    return approval_store.get_approval(session, workspace_id, approval_id)


def _approve_classification(session, approval, category, user_id):
    suggested = approval.payload["suggested_category"]
    final_category = category or suggested

    if final_category not in CATEGORIES:
        raise ApprovalConflict(f"Unknown category: {final_category}")

    if final_category == suggested:
        source = "AI Approved"
        reason = approval.payload["reason"]
    else:
        source = "Human Correction"
        reason = (
            f"Human changed the AI suggestion from "
            f"{suggested} to {final_category}."
        )

    _claim(
        session,
        approval,
        "approved",
        {"approved": True, "category": final_category},
        user_id,
    )

    workspace_id = approval.workspace_id
    email = approval.customer_email
    customer = customer_store.update_customer_classification(
        session, workspace_id, email, final_category, source, reason
    )
    _log_decision(approval, "approved")

    # The email wording depends on the category, so refresh any pending email
    pending_email = approval_store.list_approvals(
        session, workspace_id, "pending", "email", email
    )

    if customer is not None and pending_email:
        request_email_approval(
            session,
            workspace_id,
            create_email_preview({
                "name": customer.name,
                "email": customer.email,
                "category": customer.category,
                "quote_usd": customer.quote_usd or "",
            }),
        )

    session.commit()


def _approve_email(session, approval, user_id):
    # Never email a customer whose category is still unreviewed
    unreviewed = approval_store.list_approvals(
        session,
        approval.workspace_id,
        "pending",
        "classification",
        approval.customer_email,
    )

    if unreviewed:
        raise ApprovalConflict(
            "Review this customer's classification before approving the email."
        )

    # Claim first so a retry or double click can never send twice
    _claim(session, approval, "approved", {"approved": True}, user_id)

    status = "sent" if send_email(approval.payload) else "failed"
    approval_store.set_approval_status(
        session, approval.workspace_id, approval.id, status
    )
    _log_decision(approval, status)
