"""
E-commerce actions for workflows: invoices and checkout tracking.

Checkout tracking makes abandoned-cart reminders safe: order workflows
record each order's checkout as completed, and the cart workflow asks
`checkout_status` before emailing. If no order has ever been recorded in
the workspace, the status is unknown (`completed: null`), so a reminder is
never sent to someone who may already have bought.
"""

from sqlalchemy import func, select

from autoflow.commerce import invoices
from autoflow.commerce.orders import OrderError, parse_order
from autoflow.engine.actions import Action, ActionError, InputSpec, register
from autoflow.storage.db import utc_now
from autoflow.storage.models import CheckoutRecord, Workspace


def _create_invoice(ctx, inputs):
    try:
        order = parse_order(inputs["order"])
    except OrderError as error:
        raise ActionError(str(error), retryable=False) from error

    invoice, created = invoices.issue(ctx.session, ctx.workspace_id, order)
    workspace = ctx.session.get(Workspace, ctx.workspace_id)

    return {
        "invoice_number": invoices.display_number(workspace, invoice),
        "url": invoices.invoice_url(invoice),
        "total": invoice.total,
        "currency": invoice.currency,
        "customer_email": invoice.customer_email,
        "created": created,
    }


def _void_invoice(ctx, inputs):
    ref = str(inputs["order_ref"]).strip()
    invoice = invoices.get_by_ref(ctx.session, ctx.workspace_id, ref)
    if invoice is None:
        # Nothing was invoiced for this order, so there is nothing to undo
        return {"voided": False, "found": False}
    voided = invoices.void(ctx.session, invoice, inputs.get("reason") or "Order cancelled or refunded")
    workspace = ctx.session.get(Workspace, ctx.workspace_id)
    return {
        "voided": voided,
        "found": True,
        "invoice_number": invoices.display_number(workspace, invoice),
        "customer_email": invoice.customer_email,
    }


def _simulate_invoice(ctx, inputs):
    # Test runs check the order can be invoiced, without numbering or saving
    try:
        order = parse_order(inputs["order"])
    except OrderError as error:
        raise ActionError(str(error), retryable=False) from error

    return {
        "invoice_number": "INV-TEST",
        "url": "https://example.invalid/invoices/test",
        "total": str(order.total),
        "currency": order.currency,
        "customer_email": order.customer_email,
        # Test runs behave like the first time an order arrives
        "created": True,
        "dry_run": True,
    }


register(Action(
    name="create_invoice",
    description="Create a numbered invoice for an order (Shopify order or generic items). One invoice per order.",
    handler=_create_invoice,
    inputs={"order": InputSpec("any", description="The order data, e.g. {{trigger}} from a Shopify order webhook")},
    outputs={
        "invoice_number": "text",
        "url": "link the customer can open",
        "total": "text",
        "currency": "text",
        "customer_email": "email",
        "created": "boolean",
    },
    side_effect=True,
    idempotent=True,
    simulate=_simulate_invoice,
))


register(Action(
    name="void_invoice",
    description="Void the invoice for an order (refund or cancellation). It keeps its number; voiding twice is harmless.",
    handler=_void_invoice,
    inputs={
        "order_ref": InputSpec("any", description="The order id the invoice was made for, e.g. {{trigger.id}}"),
        "reason": InputSpec("string", required=False, description="Shown on the invoice, e.g. Refunded"),
    },
    outputs={"voided": "boolean", "found": "boolean", "invoice_number": "text", "customer_email": "email"},
    side_effect=True,
    idempotent=True,
    simulate=lambda ctx, inputs: {"voided": True, "found": True, "invoice_number": "INV-TEST", "dry_run": True},
))


def _record(session, workspace_id, token, email=None, completed=False):
    record = session.scalar(
        select(CheckoutRecord).where(CheckoutRecord.workspace_id == workspace_id, CheckoutRecord.token == token)
    )
    if record is None:
        record = CheckoutRecord(workspace_id=workspace_id, token=token, email=email)
        session.add(record)
    if completed and record.completed_at is None:
        record.completed_at = utc_now()
    session.commit()
    return record


def _record_order(ctx, inputs):
    token = inputs.get("checkout_token")
    if not token:
        # Orders without a checkout (e.g. created by staff) need no tracking
        return {"recorded": False}

    _record(ctx.session, ctx.workspace_id, str(token), inputs.get("email"), completed=True)
    return {"recorded": True}


register(Action(
    name="record_order",
    description="Remember that a checkout became an order, so cart reminders are not sent to buyers.",
    handler=_record_order,
    inputs={
        "checkout_token": InputSpec("string", required=False, description="e.g. {{trigger.checkout_token}}"),
        "email": InputSpec("string", required=False),
    },
    outputs={"recorded": "boolean"},
    side_effect=True,
    idempotent=True,
    simulate=lambda ctx, inputs: {"recorded": False, "dry_run": True},
))


def _checkout_status(ctx, inputs):
    token = str(inputs["checkout_token"])

    record = ctx.session.scalar(
        select(CheckoutRecord).where(CheckoutRecord.workspace_id == ctx.workspace_id, CheckoutRecord.token == token)
    )
    if record is not None and record.completed_at is not None:
        return {"completed": True, "tracking_active": True}

    tracking_active = (ctx.session.scalar(
        select(func.count(CheckoutRecord.id)).where(
            CheckoutRecord.workspace_id == ctx.workspace_id, CheckoutRecord.completed_at.is_not(None)
        )
    ) or 0) > 0

    # Without order tracking we cannot know, so we never claim "not completed"
    return {"completed": False if tracking_active else None, "tracking_active": tracking_active}


register(Action(
    name="checkout_status",
    description="Check whether a checkout turned into an order (needs an order workflow with record_order).",
    handler=_checkout_status,
    inputs={"checkout_token": InputSpec("string", description="e.g. {{trigger.token}} from a Shopify checkout webhook")},
    outputs={"completed": "true / false / null (unknown)", "tracking_active": "boolean"},
))
