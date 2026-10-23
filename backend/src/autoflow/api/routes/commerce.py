"""E-commerce API: business profile, invoice list and the public invoice page."""

from html import escape

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from autoflow import audit
from autoflow.api.deps import AdminAccess, MemberAccess, Session, ViewerAccess
from autoflow.commerce import invoices
from autoflow.engine.limits import get_workspace
from autoflow.storage.models import Invoice


router = APIRouter(tags=["e-commerce"])


class BusinessProfile(BaseModel):
    business_name: str | None = Field(None, max_length=200)
    business_address: str | None = Field(None, max_length=1000)
    tax_id: str | None = Field(None, max_length=100)
    invoice_prefix: str | None = Field(None, max_length=20, pattern=r"^[A-Za-z0-9\-_/]*$")


def _profile(workspace):
    return {
        "business_name": workspace.business_name,
        "business_address": workspace.business_address,
        "tax_id": workspace.tax_id,
        "invoice_prefix": workspace.invoice_prefix,
    }


@router.get("/workspaces/{workspace_id}/business")
def get_business(membership: ViewerAccess, session: Session):
    return _profile(get_workspace(session, membership.workspace_id))


@router.patch("/workspaces/{workspace_id}/business")
def update_business(request: BusinessProfile, membership: AdminAccess, session: Session):
    workspace = get_workspace(session, membership.workspace_id)
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(workspace, field, value)
    session.commit()
    return _profile(workspace)


@router.get("/workspaces/{workspace_id}/invoices")
def list_invoices(membership: ViewerAccess, session: Session):
    workspace = get_workspace(session, membership.workspace_id)
    rows = session.scalars(
        select(Invoice).where(Invoice.workspace_id == workspace.id).order_by(Invoice.number.desc()).limit(200)
    ).all()

    return [
        {
            "number": invoices.display_number(workspace, invoice),
            "order": invoice.external_ref,
            "customer_name": invoice.customer_name,
            "customer_email": invoice.customer_email,
            "total": invoice.total,
            "currency": invoice.currency,
            "issued_at": invoice.issued_at,
            "url": invoices.invoice_url(invoice),
            "id": invoice.id,
            "voided_at": invoice.voided_at,
            "void_reason": invoice.void_reason,
        }
        for invoice in rows
    ]


class VoidRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


@router.post("/workspaces/{workspace_id}/invoices/{invoice_id}/void")
def void_invoice(invoice_id: int, request: VoidRequest, membership: MemberAccess, session: Session):
    invoice = session.get(Invoice, invoice_id)
    if invoice is None or invoice.workspace_id != membership.workspace_id:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoices.void(session, invoice, request.reason):
        audit.for_member(membership, session, "invoice.voided", target=f"invoice:{invoice.id}",
                         details={"reason": request.reason})
    return {"id": invoice.id, "voided_at": invoice.voided_at, "void_reason": invoice.void_reason}


@router.get("/invoices/{token}", response_class=HTMLResponse, include_in_schema=False)
def public_invoice(token: str, session: Session):
    """The customer's printable invoice. The link itself is the secret."""

    invoice, workspace = invoices.get_public(session, token)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    e = lambda value: escape(str(value or ""))  # noqa: E731
    rows = "".join(
        f"<tr><td>{e(line['title'])}</td><td class=n>{e(line['quantity'])}</td>"
        f"<td class=n>{e(line['unit_price'])}</td><td class=n>{e(line['amount'])}</td></tr>"
        for line in invoice.lines
    )
    seller = e(workspace.business_name or workspace.name)
    address = e(workspace.business_address).replace("\n", "<br>")
    tax_id = f"<p>Tax ID: {e(workspace.tax_id)}</p>" if workspace.tax_id else ""
    number = e(invoices.display_number(workspace, invoice))
    void_banner = (
        f'<p class=void>VOID: this invoice was cancelled on {invoice.voided_at:%d %B %Y}'
        f'{" (" + e(invoice.void_reason) + ")" if invoice.void_reason else ""}. Nothing is due.</p>'
        if invoice.voided_at else ""
    )

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>Invoice {number}</title>
<style>
body{{font-family:system-ui,sans-serif;color:#0f172a;max-width:760px;margin:40px auto;padding:0 16px}}
header{{display:flex;justify-content:space-between;gap:24px;flex-wrap:wrap}}
h1{{margin:0 0 4px}} table{{width:100%;border-collapse:collapse;margin-top:24px}}
th,td{{padding:8px;border-bottom:1px solid #e2e8f0;text-align:left}} .n{{text-align:right}}
tfoot td{{border:none}} .total td{{font-weight:700;font-size:1.1em}} p{{margin:2px 0;color:#475569}}
.void{{margin-top:16px;padding:12px;border:2px solid #b91c1c;color:#b91c1c;font-weight:700}}
@media print{{button{{display:none}}}}
</style></head><body>
<header>
  <div><h1>Invoice {number}</h1><p>Order {e(invoice.external_ref)}</p>
       <p>Issued {invoice.issued_at:%d %B %Y}</p></div>
  <div><strong>{seller}</strong><p>{address}</p>{tax_id}</div>
</header>
{void_banner}
<p style="margin-top:24px"><strong>Billed to:</strong> {e(invoice.customer_name)} {e(invoice.customer_email)}</p>
<table>
  <thead><tr><th>Item</th><th class=n>Qty</th><th class=n>Unit price</th><th class=n>Amount</th></tr></thead>
  <tbody>{rows}</tbody>
  <tfoot>
    <tr><td colspan=3 class=n>Subtotal</td><td class=n>{e(invoice.subtotal)}</td></tr>
    <tr><td colspan=3 class=n>Tax</td><td class=n>{e(invoice.tax)}</td></tr>
    <tr class=total><td colspan=3 class=n>Total ({e(invoice.currency)})</td><td class=n>{e(invoice.total)}</td></tr>
  </tfoot>
</table>
<p style="margin-top:32px"><button onclick="window.print()">Print or save as PDF</button></p>
</body></html>"""

    return HTMLResponse(html, headers={"Cache-Control": "private, no-store", "X-Robots-Tag": "noindex"})
