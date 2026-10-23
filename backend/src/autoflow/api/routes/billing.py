"""Billing API: plans, usage, Stripe checkout/portal/webhooks, staff tools."""

import json
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from autoflow import audit
from autoflow.api.deps import CurrentUser, Session, ViewerAccess, require_role
from autoflow.billing import plans
from autoflow.billing import service as billing
from autoflow.billing import stripe
from autoflow.storage.models import Membership


router = APIRouter(tags=["billing"])
OwnerAccess = Annotated[Membership, Depends(require_role("owner"))]


class PlanChoice(BaseModel):
    plan: str


class BillingSettings(BaseModel):
    hard_cap: bool


def staff_user(user: CurrentUser):
    """AutoFlow team members (AUTOFLOW_STAFF_EMAILS), e.g. for invoiced pilots."""

    staff = {e.strip().lower() for e in os.getenv("AUTOFLOW_STAFF_EMAILS", "").split(",") if e.strip()}
    if user.email not in staff:
        raise HTTPException(status_code=403, detail="AutoFlow staff only.")
    return user


@router.get("/plans")
def list_plans():
    return plans.describe()


@router.get("/workspaces/{workspace_id}/billing")
def get_billing(membership: ViewerAccess, session: Session):
    return {**billing.summary(session, membership.workspace_id), "online_payments": stripe.enabled()}


@router.patch("/workspaces/{workspace_id}/billing")
def update_billing(request: BillingSettings, membership: OwnerAccess, session: Session):
    subscription = billing.ensure_subscription(session, membership.workspace_id)

    if not request.hard_cap and billing.effective_plan_name(subscription) == plans.DEFAULT_PLAN:
        raise HTTPException(status_code=409, detail="The free plan always stops at its included tasks.")

    subscription.hard_cap = request.hard_cap
    session.commit()
    audit.for_member(membership, session, "billing.hard_cap_changed", details={"hard_cap": request.hard_cap})
    return billing.summary(session, membership.workspace_id)


@router.post("/workspaces/{workspace_id}/billing/checkout")
def start_checkout(request: PlanChoice, membership: OwnerAccess, session: Session):
    if request.plan not in plans.all_plans() or request.plan == plans.DEFAULT_PLAN:
        raise HTTPException(status_code=422, detail="Choose a paid plan.")

    try:
        url = stripe.create_checkout(session, membership.workspace_id, request.plan, membership.user.email)
    except stripe.StripeError as error:
        raise HTTPException(status_code=503, detail=str(error))

    return {"url": url}


@router.post("/workspaces/{workspace_id}/billing/portal")
def open_portal(membership: OwnerAccess, session: Session):
    try:
        return {"url": stripe.create_portal(session, membership.workspace_id)}
    except stripe.StripeError as error:
        raise HTTPException(status_code=409, detail=str(error))


@router.post("/billing/stripe-webhook")
async def stripe_webhook(request: Request, session: Session):
    payload = await request.body()

    try:
        stripe.verify_signature(payload, request.headers.get("stripe-signature"))
    except stripe.InvalidSignature as error:
        raise HTTPException(status_code=400, detail=str(error))

    applied = stripe.handle_event(session, json.loads(payload))
    return {"received": True, "applied": applied}


@router.put("/admin/workspaces/{workspace_id}/plan")
def staff_set_plan(
    workspace_id: int,
    request: PlanChoice,
    session: Session,
    staff: Annotated[object, Depends(staff_user)],
):
    """Manual billing: set a workspace's plan (pilots invoiced outside Stripe)."""

    try:
        billing.set_plan(session, workspace_id, request.plan)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))

    audit.record(session, "billing.plan_set_by_staff", workspace_id=workspace_id,
                 user_id=staff.id, details={"plan": request.plan})

    return billing.summary(session, workspace_id)
