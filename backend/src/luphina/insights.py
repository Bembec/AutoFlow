"""Insights: what automation saves a shop, and what to automate or fix next.

Suggestions ("process discovery") are simple, explainable rules over the
workspace's own data: connected apps, installed templates, run results.
Each one says why it is suggested, so the owner can judge it.
"""

from collections import Counter, defaultdict
from datetime import timedelta

from sqlalchemy import select

from luphina import features
from luphina.storage.db import utc_now
from luphina.storage.models import (
    Connection,
    WebhookEndpoint,
    Workflow,
    WorkflowExecution,
    WorkflowVersion,
    Workspace,
)


WEEKS = 8
MAX_SUGGESTIONS = 5
# A workflow "fails often" from this share of failed live runs (min. runs)
FAILURE_SHARE = 0.2
FAILURE_MIN_RUNS = 5
FAILED = ("failed", "needs_attention")

ORDER_TEMPLATES = {"shopify-order-to-invoice", "woocommerce-order-to-invoice"}


def _store(connections, endpoints, installed):
    """Which shop platform the workspace uses, if we can tell."""
    signals = {c.provider for c in connections} | {e.signature_scheme for e in endpoints}
    signals |= {"woocommerce" for slug in installed if slug.startswith("woocommerce")}
    signals |= {"shopify" for slug in installed if slug.startswith("shopify")}
    if "woocommerce" in signals:
        return "woocommerce"
    if "shopify" in signals:
        return "shopify"
    return None


def summary(session, workspace: Workspace):
    now = utc_now()
    since_month = now - timedelta(days=30)
    since_weeks = now - timedelta(weeks=WEEKS)

    workflows = session.scalars(
        select(Workflow).where(Workflow.workspace_id == workspace.id, Workflow.status != "archived")
    ).all()
    minutes = {workflow.id: workflow.minutes_saved_per_run for workflow in workflows}

    live = session.execute(
        select(WorkflowExecution.workflow_id, WorkflowExecution.status, WorkflowExecution.created_at).where(
            WorkflowExecution.workspace_id == workspace.id,
            WorkflowExecution.mode == "live",
            WorkflowExecution.created_at >= since_weeks,
        )
    ).all()

    weekly = [0] * WEEKS
    month_runs = Counter()
    month_succeeded = Counter()
    month_failed = Counter()
    for workflow_id, status, created_at in live:
        succeeded = status == "succeeded"
        if succeeded and workflow_id in minutes:
            # 0 = the oldest week, WEEKS - 1 = the current one
            # Clamped: a run stamped slightly in the future (clock skew) counts as this week
            age = max(0, min(WEEKS - 1, int((now - created_at).total_seconds() // (7 * 24 * 3600))))
            weekly[WEEKS - 1 - age] += minutes[workflow_id]
        if created_at >= since_month:
            month_runs[workflow_id] += 1
            month_succeeded[workflow_id] += succeeded
            month_failed[workflow_id] += status in FAILED

    rate = workspace.time_value_per_hour

    def money(saved_minutes):
        return round(saved_minutes / 60 * rate, 2) if rate else None

    per_workflow = sorted(
        (
            {
                "id": workflow.id,
                "name": workflow.name,
                "status": workflow.status,
                "runs_30d": month_runs[workflow.id],
                "succeeded_30d": month_succeeded[workflow.id],
                "failed_30d": month_failed[workflow.id],
                "minutes_saved_30d": month_succeeded[workflow.id] * workflow.minutes_saved_per_run,
                "money_saved_30d": money(month_succeeded[workflow.id] * workflow.minutes_saved_per_run),
            }
            for workflow in workflows
        ),
        key=lambda row: row["minutes_saved_30d"],
        reverse=True,
    )

    total_minutes = sum(row["minutes_saved_30d"] for row in per_workflow)
    finished = sum(month_succeeded.values()) + sum(month_failed.values())
    return {
        "time_value": {"per_hour": rate, "currency": workspace.time_value_currency},
        "last_30_days": {
            "live_runs": sum(month_runs.values()),
            "succeeded": sum(month_succeeded.values()),
            "failed": sum(month_failed.values()),
            "success_rate": round(sum(month_succeeded.values()) / finished, 3) if finished else None,
            "minutes_saved": total_minutes,
            "money_saved": money(total_minutes),
        },
        "weekly_minutes_saved": weekly,
        "per_workflow": per_workflow,
        "suggestions": (
            suggestions(session, workspace, workflows, month_runs, month_failed)
            if features.enabled("insights_suggestions", workspace) else []
        ),
    }


def suggestions(session, workspace, workflows, month_runs, month_failed):
    """Ranked list: fixes first, then setup, then new automations."""
    now = utc_now()
    connections = session.scalars(
        select(Connection).where(Connection.workspace_id == workspace.id, Connection.status == "active")
    ).all()
    endpoints = session.scalars(select(WebhookEndpoint).where(WebhookEndpoint.workspace_id == workspace.id)).all()
    published = set(
        session.scalars(
            select(WorkflowVersion.workflow_id)
            .join(Workflow, Workflow.id == WorkflowVersion.workflow_id)
            .where(Workflow.workspace_id == workspace.id, WorkflowVersion.state == "published")
        ).all()
    )
    installed = {workflow.source_template for workflow in workflows if workflow.source_template}
    providers = {connection.provider for connection in connections}
    store = _store(connections, endpoints, installed)
    endpoint_by_workflow = {endpoint.workflow_id: endpoint for endpoint in endpoints}
    found = defaultdict(list)

    def add(group, id, title, reason, link=None, template=None, vars=None):
        # `key` + `vars` let the app show the text in the user's language
        key = id.split("-")[0] if group == "fix" else id
        found[group].append({
            "id": id, "kind": group, "key": key, "vars": vars or {},
            "title": title, "reason": reason, "link": link, "template": template,
        })

    for workflow in workflows:
        runs, failed = month_runs[workflow.id], month_failed[workflow.id]
        if runs >= FAILURE_MIN_RUNS and failed / runs >= FAILURE_SHARE:
            add(
                "fix", f"failing-{workflow.id}", f"“{workflow.name}” often fails",
                f"{failed} of its {runs} live runs in the last 30 days did not finish. "
                "Open the failed runs to see which step needs attention.",
                link=f"/workflows/{workflow.id}",
                vars={"name": workflow.name, "failed": failed, "runs": runs},
            )
        old_enough = workflow.created_at <= now - timedelta(days=1)
        if workflow.id not in published and old_enough:
            add(
                "fix", f"unpublished-{workflow.id}", f"Finish “{workflow.name}”",
                "It was set up but never switched on, so it isn't saving you any time yet.",
                link=f"/workflows/{workflow.id}",
                vars={"name": workflow.name},
            )
        endpoint = endpoint_by_workflow.get(workflow.id)
        if workflow.status == "active" and workflow.id in published and endpoint and not endpoint.last_called_at and old_enough:
            add(
                "fix", f"silent-{workflow.id}", f"“{workflow.name}” hasn't heard from your store",
                "Its webhook address has never been called. Check that it is added in your store's settings.",
                link=f"/workflows/{workflow.id}?tab=trigger",
                vars={"name": workflow.name},
            )

    has_alerts = workspace.notify_slack_connection or (workspace.notify_email and workspace.notify_smtp_connection)
    if published and not has_alerts:
        add(
            "setup", "alerts", "Get told when something needs you",
            "Workflows are live but no email or Slack alerts are set up, so approvals and failures could wait unnoticed.",
            link="/settings#notifications",
        )
    if installed & ORDER_TEMPLATES and not workspace.business_name:
        add(
            "setup", "business", "Add your business details",
            "Your invoices currently show the workspace name instead of your business name and address.",
            link="/settings#business",
        )

    order_template = "woocommerce-order-to-invoice" if store == "woocommerce" else "shopify-order-to-invoice"
    if not installed & ORDER_TEMPLATES:
        add(
            "automate", "template-order-invoice", "Send an invoice for every order",
            "Most shops write or send invoices by hand for each order. This does it the moment an order is paid, "
            "with your approval before it goes out.",
            template=order_template,
        )
    if installed & ORDER_TEMPLATES and store != "woocommerce" and "abandoned-cart-follow-up" not in installed:
        add(
            "automate", "template-abandoned-cart", "Win back abandoned carts",
            "Your store already sends orders here. The same connection can remind shoppers who leave items "
            "in their cart, and skip anyone who bought in the meantime.",
            template="abandoned-cart-follow-up",
        )
    if (store or installed & ORDER_TEMPLATES) and "review-reply-assistant" not in installed:
        add(
            "automate", "template-reviews", "Reply to every review",
            "Answering reviews quickly builds trust. AI drafts a personal reply to each one; you approve it.",
            template="review-reply-assistant",
        )
    if providers & {"imap", "smtp"} and "supplier-invoice-to-sheet" not in installed:
        add(
            "automate", "template-supplier-invoices", "Stop typing supplier invoices",
            "Your email is connected. AI can read invoices that arrive there and add them to your bookkeeping sheet.",
            template="supplier-invoice-to-sheet",
        )

    ranked = found["fix"] + found["setup"] + found["automate"]
    return ranked[:MAX_SUGGESTIONS]
