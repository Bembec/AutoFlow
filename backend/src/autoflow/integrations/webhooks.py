"""
Inbound webhooks: other apps start a workflow by POSTing to a secret URL.

Every request must be signed with the endpoint's secret:

- "autoflow" scheme (for any app or your own code):
      X-AutoFlow-Timestamp: <unix seconds>
      X-AutoFlow-Signature: sha256=<hex HMAC-SHA256(secret, "<timestamp>.<raw body>")>
  Requests older than 5 minutes are rejected (replay protection).
- "shopify" scheme (Shopify order/customer webhooks):
      X-Shopify-Hmac-Sha256: <base64 HMAC-SHA256(secret, raw body)>

Retried deliveries are recognised by Idempotency-Key, X-Shopify-Webhook-Id
or X-Request-Id and never start a second execution.
"""

import base64
import hashlib
import hmac
import re
import json
import secrets as random_secrets
import time

from sqlalchemy import select

from autoflow import config
from autoflow.engine import service as engine
from autoflow.engine.definition import WorkflowDefinition
from autoflow.security import vault
from autoflow.storage.db import utc_now
from autoflow.storage.models import WebhookEndpoint


SCHEMES = ("autoflow", "shopify", "woocommerce")
# Headers carrying each scheme's base64 HMAC-SHA256 of the raw body
BASE64_SIGNATURE_HEADERS = {"shopify": "x-shopify-hmac-sha256", "woocommerce": "x-wc-webhook-signature"}
# WooCommerce checks a new webhook with a form-encoded ping
WOOCOMMERCE_PING = re.compile(rb"webhook_id=\d+")
MAX_BODY_BYTES = 256 * 1024
MAX_CLOCK_SKEW_SECONDS = 300


class WebhookPing(Exception):
    """A connectivity check from the sending app, not an event."""


class WebhookRejected(Exception):
    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = status_code


def url_for(endpoint):
    return f"{config.PUBLIC_URL}/hooks/{endpoint.public_id}"


def get_endpoint(session, workspace_id, workflow_id):
    return session.scalar(
        select(WebhookEndpoint).where(
            WebhookEndpoint.workspace_id == workspace_id,
            WebhookEndpoint.workflow_id == workflow_id,
        )
    )


def enable(session, workspace_id, workflow_id, scheme="autoflow", secret=None):
    """Create the endpoint, or rotate its secret. Returns (endpoint, secret).

    The secret is shown once. For Shopify, pass the app's own webhook
    secret, since Shopify signs with it.
    """

    if scheme not in SCHEMES:
        raise ValueError(f"Unknown signature scheme: {scheme}")

    workflow = engine.get_workflow(session, workspace_id, workflow_id)
    secret = secret or random_secrets.token_urlsafe(32)
    endpoint = get_endpoint(session, workspace_id, workflow.id)

    if endpoint is None:
        endpoint = WebhookEndpoint(
            workspace_id=workspace_id,
            workflow_id=workflow.id,
            public_id=random_secrets.token_urlsafe(24),
        )
        session.add(endpoint)

    endpoint.signature_scheme = scheme
    endpoint.encrypted_secret = vault.encrypt_json({"secret": secret})
    session.commit()
    return endpoint, secret


def disable(session, workspace_id, workflow_id):
    endpoint = get_endpoint(session, workspace_id, workflow_id)
    if endpoint is not None:
        session.delete(endpoint)
        session.commit()


def sign(secret, body, timestamp=None):
    """Produce AutoFlow-scheme headers (for senders and tests)."""

    timestamp = str(int(timestamp or time.time()))
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    return {"X-AutoFlow-Timestamp": timestamp, "X-AutoFlow-Signature": f"sha256={digest}"}


def _verify(endpoint, body, headers):
    secret = vault.decrypt_json(endpoint.encrypted_secret)["secret"].encode()

    if endpoint.signature_scheme in BASE64_SIGNATURE_HEADERS:
        expected = base64.b64encode(hmac.new(secret, body, hashlib.sha256).digest()).decode()
        provided = headers.get(BASE64_SIGNATURE_HEADERS[endpoint.signature_scheme], "")
        if not hmac.compare_digest(expected, provided):
            raise WebhookRejected(401, "Invalid signature.")
        return

    timestamp = headers.get("x-autoflow-timestamp", "")
    provided = headers.get("x-autoflow-signature", "")

    if not timestamp.isdigit() or abs(time.time() - int(timestamp)) > MAX_CLOCK_SKEW_SECONDS:
        raise WebhookRejected(401, "Missing or stale timestamp.")

    expected = "sha256=" + hmac.new(secret, f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, provided):
        raise WebhookRejected(401, "Invalid signature.")


def receive(session, public_id, body, headers):
    """Verify a delivery and start the workflow. Returns (execution, created)."""

    endpoint = session.scalar(select(WebhookEndpoint).where(WebhookEndpoint.public_id == public_id))

    if endpoint is None:
        raise WebhookRejected(404, "Unknown webhook.")

    if len(body) > MAX_BODY_BYTES:
        raise WebhookRejected(413, "Payload too large.")

    if endpoint.signature_scheme == "woocommerce" and WOOCOMMERCE_PING.fullmatch(body.strip()):
        # Answer the setup ping so WooCommerce keeps the webhook active; no run starts
        raise WebhookPing()

    headers = {key.lower(): value for key, value in headers.items()}
    _verify(endpoint, body, headers)

    try:
        payload = json.loads(body or b"{}")
    except ValueError as error:
        raise WebhookRejected(400, "The body must be JSON.") from error

    if not isinstance(payload, dict):
        payload = {"data": payload}

    workflow = engine.get_workflow(session, endpoint.workspace_id, endpoint.workflow_id)
    published = engine.version_in_state(workflow, "published")

    if published is None or workflow.status != "active":
        raise WebhookRejected(409, "The workflow is not published.")

    if WorkflowDefinition.model_validate(published.definition).trigger.type != "webhook":
        raise WebhookRejected(409, "The workflow is not triggered by webhooks.")

    delivery_id = (
        headers.get("idempotency-key")
        or headers.get("x-shopify-webhook-id")
        or headers.get("x-wc-webhook-delivery-id")
        or headers.get("x-request-id")
    )

    endpoint.last_called_at = utc_now()
    session.commit()

    try:
        return engine.start_execution(
            session,
            endpoint.workspace_id,
            endpoint.workflow_id,
            mode="live",
            payload=payload,
            idempotency_key=f"webhook:{endpoint.id}:{delivery_id}"[:200] if delivery_id else None,
        )
    except engine.WorkflowError as error:
        raise WebhookRejected(409, str(error)) from error
