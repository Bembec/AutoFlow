"""
Invoices: numbered per workspace, one per order, viewable by the customer
through an unguessable link.
"""

import secrets

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from autoflow import config
from autoflow.storage.models import Invoice, Workspace


def invoice_url(invoice):
    return f"{config.PUBLIC_URL}/invoices/{invoice.public_token}"


def display_number(workspace, invoice):
    return f"{workspace.invoice_prefix or ''}{invoice.number:05d}"


def get_by_ref(session, workspace_id, external_ref):
    return session.scalar(
        select(Invoice).where(Invoice.workspace_id == workspace_id, Invoice.external_ref == external_ref)
    )


def issue(session, workspace_id, order, attempts=3):
    """Create the invoice for an order, or return the existing one.

    Returns (invoice, created). The same order never gets two invoices,
    and numbers stay unique even if two runs race.
    """

    existing = get_by_ref(session, workspace_id, order.external_ref)
    if existing is not None:
        return existing, False

    for _ in range(attempts):
        last = session.scalar(select(func.max(Invoice.number)).where(Invoice.workspace_id == workspace_id))
        invoice = Invoice(
            workspace_id=workspace_id,
            number=(last or 0) + 1,
            external_ref=order.external_ref,
            customer_name=order.customer_name,
            customer_email=order.customer_email,
            currency=order.currency,
            lines=order.lines,
            subtotal=str(order.subtotal),
            tax=str(order.tax),
            total=str(order.total),
            public_token=secrets.token_urlsafe(24),
        )
        session.add(invoice)
        try:
            session.commit()
            return invoice, True
        except IntegrityError:
            session.rollback()
            # Another run created this order's invoice, or took the number
            existing = get_by_ref(session, workspace_id, order.external_ref)
            if existing is not None:
                return existing, False

    raise RuntimeError("Could not allocate an invoice number; try again.")


def get_public(session, token):
    invoice = session.scalar(select(Invoice).where(Invoice.public_token == token))
    if invoice is None:
        return None, None
    return invoice, session.get(Workspace, invoice.workspace_id)
