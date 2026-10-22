"""
Stripe payments: Checkout for upgrades, the customer portal for managing
cards, invoices, downgrades and cancellations, and signed webhooks that
keep each workspace's subscription in sync.

Calls use Stripe's REST API directly. Configuration:
    STRIPE_SECRET_KEY        sk_live_... / sk_test_...
    STRIPE_WEBHOOK_SECRET    whsec_... (from the webhook endpoint)
    STRIPE_PRICE_<PLAN>      price id per plan, e.g. STRIPE_PRICE_STARTER
"""

import hashlib
import hmac
import os
import time
from datetime import datetime, timezone

import requests
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from autoflow import config
from autoflow.billing import plans
from autoflow.billing.service import ensure_subscription
from autoflow.storage.models import ProcessedStripeEvent, Subscription


API = "https://api.stripe.com/v1"
SIGNATURE_TOLERANCE_SECONDS = 300

STATUS_MAP = {
    "active": "active",
    "trialing": "trialing",
    "past_due": "past_due",
    "unpaid": "past_due",
    "incomplete": "past_due",
    "incomplete_expired": "canceled",
    "canceled": "canceled",
    "paused": "past_due",
}


class StripeError(Exception):
    """Stripe is not configured or rejected a request."""


class InvalidSignature(Exception):
    """A webhook did not come from Stripe."""


def enabled():
    return bool(os.getenv("STRIPE_SECRET_KEY"))


def _post(path, data):
    if not enabled():
        raise StripeError("Online payments are not configured on this server.")

    response = requests.post(f"{API}{path}", data=data, auth=(os.getenv("STRIPE_SECRET_KEY"), ""), timeout=20)

    if response.status_code >= 400:
        message = response.json().get("error", {}).get("message", response.text[:200])
        raise StripeError(f"Stripe: {message}")

    return response.json()


def create_checkout(session, workspace_id, plan_name, customer_email):
    price = plans.stripe_price_id(plan_name)
    if not price:
        raise StripeError(f"The {plan_name} plan cannot be bought online yet.")

    subscription = ensure_subscription(session, workspace_id)
    session.commit()

    data = {
        "mode": "subscription",
        "line_items[0][price]": price,
        "line_items[0][quantity]": 1,
        "client_reference_id": str(workspace_id),
        "metadata[workspace_id]": str(workspace_id),
        "metadata[plan]": plan_name,
        "subscription_data[metadata][workspace_id]": str(workspace_id),
        "success_url": f"{config.PUBLIC_URL}/billing?checkout=success",
        "cancel_url": f"{config.PUBLIC_URL}/billing?checkout=cancelled",
    }
    if subscription.stripe_customer_id:
        data["customer"] = subscription.stripe_customer_id
    else:
        data["customer_email"] = customer_email

    return _post("/checkout/sessions", data)["url"]


def create_portal(session, workspace_id):
    subscription = ensure_subscription(session, workspace_id)

    if not subscription.stripe_customer_id:
        raise StripeError("This workspace has no online billing account yet.")

    return _post("/billing_portal/sessions", {
        "customer": subscription.stripe_customer_id,
        "return_url": f"{config.PUBLIC_URL}/billing",
    })["url"]


def verify_signature(payload, header, secret=None, now=None):
    """Check a Stripe-Signature header: t=<ts>,v1=<hex hmac of "t.payload">."""

    secret = secret or os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        raise InvalidSignature("Stripe webhooks are not configured.")

    parts = [item.split("=", 1) for item in (header or "").split(",") if "=" in item]
    timestamp = next((value for key, value in parts if key == "t"), "")
    signatures = [value for key, value in parts if key == "v1"]

    if not timestamp.isdigit() or abs((now or time.time()) - int(timestamp)) > SIGNATURE_TOLERANCE_SECONDS:
        raise InvalidSignature("Missing or stale timestamp.")

    expected = hmac.new(secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, signature) for signature in signatures):
        raise InvalidSignature("Signature mismatch.")


def _timestamp(value):
    return datetime.fromtimestamp(int(value), tz=timezone.utc) if value else None


def _find_subscription(session, workspace_id=None, customer=None, subscription_id=None):
    if workspace_id:
        return ensure_subscription(session, int(workspace_id))

    for column, value in ((Subscription.stripe_subscription_id, subscription_id), (Subscription.stripe_customer_id, customer)):
        if value:
            found = session.scalar(select(Subscription).where(column == value))
            if found is not None:
                return found

    return None


def handle_event(session, event):
    """Apply one Stripe event. Returns False for duplicates or ignored types."""

    session.add(ProcessedStripeEvent(id=event["id"], type=event["type"]))
    try:
        session.flush()
    except IntegrityError:
        # Stripe retries deliveries; each event is applied once
        session.rollback()
        return False

    kind, obj = event["type"], event["data"]["object"]

    if kind == "checkout.session.completed":
        workspace_id = obj.get("client_reference_id") or obj.get("metadata", {}).get("workspace_id")
        subscription = _find_subscription(session, workspace_id=workspace_id)
        if subscription is not None:
            subscription.provider = "stripe"
            subscription.stripe_customer_id = obj.get("customer")
            subscription.stripe_subscription_id = obj.get("subscription")
            subscription.plan = obj.get("metadata", {}).get("plan") or subscription.plan
            subscription.status = "active"

    elif kind in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
        subscription = _find_subscription(
            session,
            workspace_id=obj.get("metadata", {}).get("workspace_id"),
            customer=obj.get("customer"),
            subscription_id=obj.get("id"),
        )
        if subscription is not None:
            item = (obj.get("items", {}).get("data") or [{}])[0]
            subscription.provider = "stripe"
            subscription.stripe_customer_id = obj.get("customer") or subscription.stripe_customer_id
            subscription.stripe_subscription_id = obj.get("id")
            subscription.plan = plans.plan_for_stripe_price(item.get("price", {}).get("id")) or subscription.plan
            subscription.status = "canceled" if kind.endswith("deleted") else STATUS_MAP.get(obj.get("status"), "past_due")
            subscription.cancel_at_period_end = bool(obj.get("cancel_at_period_end"))
            # Newer API versions keep the period on the subscription item
            subscription.current_period_start = _timestamp(obj.get("current_period_start") or item.get("current_period_start"))
            subscription.current_period_end = _timestamp(obj.get("current_period_end") or item.get("current_period_end"))

    elif kind in ("invoice.payment_failed", "invoice.paid"):
        subscription = _find_subscription(session, customer=obj.get("customer"), subscription_id=obj.get("subscription"))
        if subscription is not None:
            if kind == "invoice.payment_failed":
                subscription.status = "past_due"
            elif subscription.status == "past_due":
                subscription.status = "active"

    session.commit()
    return True
