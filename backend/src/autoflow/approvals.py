"""
Human-in-the-loop decisions for AutoFlow.

Sensitive actions (accepting an AI classification, emailing a customer)
wait as pending approvals until a person approves, corrects or rejects
them. Each approval can be decided exactly once.
"""

from autoflow.activity_log import timestamp_now, write_log_lines
from autoflow.emails.sender import send_email
from autoflow.emails.templates import create_email_preview
from autoflow.storage import approvals as approval_store
from autoflow.storage import database


CATEGORIES = ("Sales", "Support", "Other")


class ApprovalNotFound(Exception):
    """No approval exists with the requested id."""


class ApprovalConflict(Exception):
    """The approval cannot be decided in its current state."""


def request_classification_review(customer, ai_result):
    """Queue an AI category suggestion for human review."""

    approval_store.upsert_pending_approval(
        "classification",
        customer["email"].strip().lower(),
        {
            "name": customer["name"],
            "message": customer["message"],
            "suggested_category": ai_result["category"],
            "reason": ai_result["reason"],
        },
    )


def request_email_approval(email_preview):
    """Queue an outgoing email for human approval."""

    approval_store.upsert_pending_approval(
        "email",
        email_preview["to"].strip().lower(),
        email_preview,
    )


def _log_decision(approval, status):
    write_log_lines([
        f"{timestamp_now()} | APPROVAL | {approval['kind'].upper()} "
        f"#{approval['id']} {status.upper()} | "
        f"Email: {approval['customer_email']}"
    ])


def _get_pending(approval_id):
    approval = approval_store.get_approval(approval_id)

    if approval is None:
        raise ApprovalNotFound(approval_id)

    if approval["status"] != "pending":
        raise ApprovalConflict(
            f"Approval {approval_id} is already {approval['status']}."
        )

    return approval


def _claim(approval, status, decision):
    # Only one caller can move a pending approval forward
    if not approval_store.claim_pending_approval(
        approval["id"], status, decision
    ):
        raise ApprovalConflict(
            f"Approval {approval['id']} was decided by someone else."
        )


def reject(approval_id):
    """Reject a pending approval; nothing is changed or sent."""

    approval = _get_pending(approval_id)
    _claim(approval, "rejected", {"approved": False})
    _log_decision(approval, "rejected")

    return approval_store.get_approval(approval_id)


def approve(approval_id, category=None):
    """Approve a pending approval and carry out its action.

    For classifications, `category` optionally corrects the AI suggestion.
    """

    approval = _get_pending(approval_id)

    if approval["kind"] == "classification":
        _approve_classification(approval, category)
    else:
        if category is not None:
            raise ApprovalConflict("A category only applies to classifications.")
        _approve_email(approval)

    return approval_store.get_approval(approval_id)


def _approve_classification(approval, category):
    suggested = approval["payload"]["suggested_category"]
    final_category = category or suggested

    if final_category not in CATEGORIES:
        raise ApprovalConflict(f"Unknown category: {final_category}")

    if final_category == suggested:
        source = "AI Approved"
        reason = approval["payload"]["reason"]
    else:
        source = "Human Correction"
        reason = (
            f"Human changed the AI suggestion from "
            f"{suggested} to {final_category}."
        )

    _claim(approval, "approved", {"approved": True, "category": final_category})

    email = approval["customer_email"]
    database.update_customer_classification(email, final_category, source, reason)
    _log_decision(approval, "approved")

    # The email wording depends on the category, so refresh any pending email
    customer = database.get_customer_by_email(email)
    pending_emails = [
        pending
        for pending in approval_store.list_approvals("pending", "email")
        if pending["customer_email"] == email
    ]

    if customer is not None and pending_emails:
        request_email_approval(create_email_preview(customer))


def _approve_email(approval):
    email = approval["customer_email"]

    # Never email a customer whose category is still unreviewed
    unreviewed = [
        pending
        for pending in approval_store.list_approvals("pending", "classification")
        if pending["customer_email"] == email
    ]

    if unreviewed:
        raise ApprovalConflict(
            "Review this customer's classification before approving the email."
        )

    # Claim first so a retry or double click can never send twice
    _claim(approval, "approved", {"approved": True})

    status = "sent" if send_email(approval["payload"]) else "failed"
    approval_store.set_approval_status(approval["id"], status)
    _log_decision(approval, status)
