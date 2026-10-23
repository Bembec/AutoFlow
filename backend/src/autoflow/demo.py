"""
Seeded demo workspace for staging, sales demos and screenshots.

    python -m autoflow.demo                      # demo@autoflow.example
    python -m autoflow.demo --email you@example.com --password '...'

Creates (once; running it again changes nothing) a shop called "Demo Mug
Shop" with business details, a mailbox connection that cannot send, the
three e-commerce templates switched on, eight weeks of past runs and
invoices, and one email waiting for approval. Nothing reaches the outside
world: the mailbox points at an unreachable host and the history is
written directly, not executed.
"""

import argparse
import copy
from datetime import timedelta

from sqlalchemy import select

from autoflow.accounts import service as accounts
from autoflow.billing import service as billing
from autoflow.commerce import invoices
from autoflow.commerce.orders import parse_order
from autoflow.engine import service as engine
from autoflow.engine.definition import WorkflowDefinition
from autoflow.engine.templates import TEMPLATES
from autoflow.engine.templates_ecommerce import SAMPLE_SHOPIFY_ORDER
from autoflow.integrations import connections
from autoflow.storage.db import utc_now
from autoflow.storage.models import Membership, StepExecution, Workflow, WorkflowExecution, Workspace

DEMO_EMAIL = "demo@autoflow.example"
DEMO_PASSWORD = "demo-password-2026"
WORKSPACE_NAME = "Demo Mug Shop"
TEMPLATE_MINUTES = {
    "shopify-order-to-invoice": 6,
    "abandoned-cart-follow-up": 4,
    "review-reply-assistant": 8,
}
CUSTOMERS = ["Ada Lovelace", "Grace Hopper", "Alan Turing", "Katherine Johnson", "Linus Pauling", "Mary Somerville"]


def _demo_workspace(session, user):
    return session.scalar(
        select(Workspace)
        .join(Membership, Membership.workspace_id == Workspace.id)
        .where(Membership.user_id == user.id, Workspace.name == WORKSPACE_NAME)
    )


def _order(index):
    order = copy.deepcopy(SAMPLE_SHOPIFY_ORDER)
    name = CUSTOMERS[index % len(CUSTOMERS)]
    first, _, last = name.partition(" ")
    email = f"{first.lower()}.{index}@example.com"
    order.update({"id": 9_100_000 + index, "name": f"#{1100 + index}", "email": email, "checkout_token": f"demo-{index}"})
    order["customer"] = {"first_name": first, "last_name": last, "email": email}
    return order


def _history_run(session, workspace, workflow, when, status, order=None):
    """Write a finished past run directly (nothing is executed or sent)."""
    version = next(v for v in workflow.versions if v.state == "published")
    definition = WorkflowDefinition.model_validate(version.definition)
    execution = WorkflowExecution(
        workspace_id=workspace.id, workflow_id=workflow.id, version_id=version.id, mode="live",
        status=status, trigger_payload=order or {}, created_at=when, started_at=when,
        finished_at=when + timedelta(seconds=4),
        error={"failed": "Step send failed: The mail server rejected the login. Reconnect the account.",
               "needs_attention": "Step send may or may not have completed. Check before retrying."}.get(status),
    )
    session.add(execution)
    session.flush()
    for position, step in enumerate(definition.steps):
        last = position == len(definition.steps) - 1
        step_status = status if last and status in ("failed",) else "succeeded"
        if last and status == "needs_attention":
            step_status = "failed"
        session.add(StepExecution(
            execution_id=execution.id, step_id=step.id, position=position, action=step.action,
            status=step_status, attempts=1, input={}, output={} if step_status == "succeeded" else None,
            error=execution.error if step_status == "failed" else None,
            started_at=when, finished_at=when + timedelta(seconds=position + 1),
        ))
    return execution


def seed(session, email=DEMO_EMAIL, password=DEMO_PASSWORD):
    """Create the demo workspace if it doesn't exist. Returns (workspace, created)."""

    user = accounts.get_user_by_email(session, email)
    new_user = user is None
    if new_user:
        user = accounts.register_user(session, email, "Demo Owner", password)
    workspace = _demo_workspace(session, user)
    if workspace is not None:
        return workspace, False

    if new_user:
        # Use the account's own (first) workspace, so sign-in opens the demo shop
        workspace = session.scalar(
            select(Workspace).join(Membership, Membership.workspace_id == Workspace.id)
            .where(Membership.user_id == user.id)
        )
        workspace.name = WORKSPACE_NAME
    else:
        workspace = accounts.create_workspace(session, user, WORKSPACE_NAME)
    workspace.trusted_at = utc_now()
    workspace.business_name = WORKSPACE_NAME + " Ltd"
    workspace.business_address = "1 Market Street\nSample Town"
    workspace.invoice_prefix = "DMS-"
    workspace.time_value_per_hour = 25
    workspace.time_value_currency = "EUR"
    session.commit()
    billing.set_plan(session, workspace.id, "growth")

    connections.create_connection(
        session, workspace.id, "smtp", "mailbox",
        secrets={"password": "demo-only-not-a-real-password"},
        # .invalid never resolves, so this mailbox can never send anything
        config={"host": "smtp.demo.invalid", "username": "hello@demo-mug-shop.invalid",
                "from_address": "hello@demo-mug-shop.invalid"},
        user_id=user.id,
    )

    workflows = {}
    for slug, minutes in TEMPLATE_MINUTES.items():
        template = TEMPLATES[slug]
        workflow = engine.create_workflow(
            session, workspace.id, template["name"], template["definition"], template["description"],
            user_id=user.id, minutes_saved_per_run=minutes, source_template=slug,
        )
        engine.publish(session, workspace.id, workflow.id)
        workflows[slug] = session.get(Workflow, workflow.id)

    # Eight weeks of history, growing week by week like a shop adopting automation
    now = utc_now()
    index = 0
    for week in range(8):
        for slot in range(3 + week):
            # At least 3 hours ago, so the follow-up runs below are in the past too
            when = now - timedelta(weeks=7 - week, days=slot % 6, hours=slot + 3)
            status = "succeeded"
            if index % 23 == 7:
                status = "failed"
            elif index % 31 == 11:
                status = "needs_attention"
            order = _order(index)
            _history_run(session, workspace, workflows["shopify-order-to-invoice"], when, status, order)
            invoice, _ = invoices.issue(session, workspace.id, parse_order(order))
            invoice.issued_at = when
            if slot % 2 == 0:
                _history_run(session, workspace, workflows["abandoned-cart-follow-up"], when + timedelta(hours=1), "succeeded")
            if slot % 3 == 0:
                _history_run(session, workspace, workflows["review-reply-assistant"], when + timedelta(hours=2), "succeeded")
            index += 1
    session.commit()

    # One fresh order waiting for the owner's approval (the email is never sent)
    engine.start_execution(
        session, workspace.id, workflows["shopify-order-to-invoice"].id, mode="live",
        payload=_order(index), user_id=user.id,
    )
    return workspace, True


def main():
    from autoflow.storage import initialize_storage
    from autoflow.storage.db import session_scope

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", default=DEMO_EMAIL)
    parser.add_argument("--password", default=DEMO_PASSWORD)
    args = parser.parse_args()

    initialize_storage()
    with session_scope() as session:
        workspace, created = seed(session, args.email.strip().lower(), args.password)
        print(f"{'Created' if created else 'Already there'}: workspace {workspace.id} \"{workspace.name}\"")
        print(f"Sign in as {args.email} / {args.password}")


if __name__ == "__main__":
    main()
