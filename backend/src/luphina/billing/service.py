"""
Plans, usage metering and plan limits for each workspace.

Billable task (the roadmap's definition): one workflow step that completes
successfully, in a live run, and calls an app or an AI model. Failed steps,
retries and test runs are free, so customers never pay for Luphina's
errors. Each billable step creates one BillableEvent, unique per step run,
so a resumed or retried execution can never be billed twice.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select

from luphina.billing import plans
from luphina.storage.models import BillableEvent, Membership, Subscription, Workflow


class PlanLimitReached(Exception):
    """The workspace's plan does not allow this."""


ALERT_THRESHOLDS = (0.8, 1.0)


def get_subscription(session, workspace_id):
    """The workspace's subscription (a free-plan default if none is stored)."""

    subscription = session.scalar(
        select(Subscription).where(Subscription.workspace_id == workspace_id)
    )
    return subscription or Subscription(
        workspace_id=workspace_id, plan=plans.DEFAULT_PLAN, status="active", provider="manual", hard_cap=True
    )


def ensure_subscription(session, workspace_id):
    """Like get_subscription, but stored so it can be changed."""

    subscription = get_subscription(session, workspace_id)
    if subscription.id is None:
        session.add(subscription)
        session.flush()
    return subscription


def effective_plan_name(subscription):
    # A cancelled subscription falls back to the free plan;
    # past_due keeps the plan during the payment-retry grace period
    if subscription.status == "canceled":
        return plans.DEFAULT_PLAN
    return subscription.plan


def billing_period(subscription, now=None):
    """(start, end) of the current period: the provider's, or the calendar month."""

    now = now or datetime.now(timezone.utc)

    if (
        subscription.current_period_start
        and subscription.current_period_end
        and subscription.current_period_start <= now < subscription.current_period_end
    ):
        return subscription.current_period_start, subscription.current_period_end

    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    end = datetime(now.year + (now.month == 12), now.month % 12 + 1, 1, tzinfo=timezone.utc)
    return start, end


def billable_tasks(session, workspace_id, start, end):
    return session.scalar(
        select(func.coalesce(func.sum(BillableEvent.quantity), 0)).where(
            BillableEvent.workspace_id == workspace_id,
            BillableEvent.created_at >= start,
            BillableEvent.created_at < end,
        )
    ) or 0


def is_billable(action, mode, output=None):
    """Live steps that call an app or AI model.

    Without `output` (before the step runs) this says whether the step
    *may* be billable, which is when the plan limit is checked.
    """

    if mode != "live" or not action.uses_network:
        return False

    if action.billable is not None and output is not None:
        return bool(action.billable(output))

    return True


def check_can_run_billable(session, workspace_id):
    subscription = get_subscription(session, workspace_id)
    plan = plans.get_plan(effective_plan_name(subscription))
    included = plan["included_tasks"]

    if included is None or not subscription.hard_cap:
        return

    start, end = billing_period(subscription)
    if billable_tasks(session, workspace_id, start, end) >= included:
        raise PlanLimitReached(
            f"The {plan['label']} plan's {included:,} tasks for this period are used up. "
            f"Upgrade your plan to keep workflows running."
        )


def record_billable(session, workspace_id, step_execution, action_name, quantity=1):
    """Add the billable event for a step (flushed with the step's success)."""

    already = session.scalar(
        select(BillableEvent).where(BillableEvent.step_execution_id == step_execution.id)
    )
    if already is None:
        session.add(BillableEvent(
            workspace_id=workspace_id,
            step_execution_id=step_execution.id,
            action=action_name,
            quantity=quantity,
        ))


def check_can_create_workflow(session, workspace_id):
    plan = plans.get_plan(effective_plan_name(get_subscription(session, workspace_id)))
    limit = plan["max_workflows"]

    if limit is None:
        return

    count = session.scalar(
        select(func.count(Workflow.id)).where(
            Workflow.workspace_id == workspace_id, Workflow.status != "archived"
        )
    )
    if count >= limit:
        raise PlanLimitReached(
            f"The {plan['label']} plan allows {limit} workflows. Archive one or upgrade."
        )


def check_can_add_member(session, workspace_id):
    plan = plans.get_plan(effective_plan_name(get_subscription(session, workspace_id)))
    limit = plan["max_seats"]

    if limit is None:
        return

    count = session.scalar(select(func.count(Membership.id)).where(Membership.workspace_id == workspace_id))
    if count >= limit:
        raise PlanLimitReached(f"The {plan['label']} plan includes {limit} seat(s). Upgrade to add more people.")


def set_plan(session, workspace_id, plan_name, hard_cap=None):
    """Change the plan directly (manual billing, e.g. invoiced pilots)."""

    if plan_name not in plans.all_plans():
        raise ValueError(f"Unknown plan: {plan_name}")

    subscription = ensure_subscription(session, workspace_id)
    subscription.plan = plan_name
    subscription.status = "active"
    if hard_cap is not None:
        subscription.hard_cap = hard_cap
    session.commit()
    return subscription


def summary(session, workspace_id, now=None):
    now = now or datetime.now(timezone.utc)
    subscription = get_subscription(session, workspace_id)
    plan_name = effective_plan_name(subscription)
    plan = plans.get_plan(plan_name)
    start, end = billing_period(subscription, now)

    used = billable_tasks(session, workspace_id, start, end)
    included = plan["included_tasks"]

    # Straight-line projection of this period's usage
    elapsed = max((now - start).total_seconds(), 3600)
    projected = round(used * (end - start).total_seconds() / elapsed)

    alerts = []
    if included:
        share = used / included
        for threshold in reversed(ALERT_THRESHOLDS):
            if share >= threshold:
                alerts.append(
                    "All included tasks are used; billable steps are paused until you upgrade."
                    if threshold == 1.0 and subscription.hard_cap
                    else f"{int(threshold * 100)}% of this period's included tasks are used."
                )
                break
        if projected > included and share < 1.0:
            alerts.append(f"At the current pace you will need about {projected:,} tasks this period.")

    from luphina.engine import limits

    ai = limits.ai_budget(session, workspace_id)
    if ai["budget_usd"] and ai["estimated_cost_usd"] >= 0.8 * ai["budget_usd"]:
        alerts.append(
            "This period's AI budget is used up; AI steps are paused until the next period."
            if ai["estimated_cost_usd"] + ai["cost_per_call_usd"] > ai["budget_usd"]
            else "80% of this period's AI budget is used."
        )

    if subscription.status == "past_due":
        alerts.append("The last payment failed. Update your payment method to avoid interruption.")

    workflows = session.scalar(
        select(func.count(Workflow.id)).where(Workflow.workspace_id == workspace_id, Workflow.status != "archived")
    )
    seats = session.scalar(select(func.count(Membership.id)).where(Membership.workspace_id == workspace_id))

    return {
        "plan": {"name": plan_name, **plan},
        "status": subscription.status,
        "provider": subscription.provider,
        "cancel_at_period_end": subscription.cancel_at_period_end,
        "hard_cap": subscription.hard_cap,
        "period": {"start": start, "end": end},
        "usage": {
            "billable_tasks": used,
            "included_tasks": included,
            "projected_tasks": projected,
        },
        "limits": {
            "workflows": {"used": workflows, "max": plan["max_workflows"]},
            "seats": {"used": seats, "max": plan["max_seats"]},
        },
        "ai": {key: ai[key] for key in ("calls", "estimated_cost_usd", "budget_usd", "cost_per_call_usd")},
        "alerts": alerts,
    }
