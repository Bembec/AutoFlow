"""
Per-workspace safety limits, counted per UTC day.

- executions started
- AI model calls (AI action attempts, test and live: both cost money)
- emails sent (live sends that succeeded)

Hitting a limit stops the run or step with a clear message instead of
letting a runaway workflow spend money or spam customers.

Brand-new workspaces get lower limits for their first days (abuse
prevention) until staff mark them trusted. AI calls also count against
a monthly AI budget per plan, estimated in USD, so one workspace can't
erase the month's margin.
"""

import os
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import func, select

from autoflow.storage.models import AIUsageEvent, StepExecution, WorkflowExecution, Workspace


EMAIL_ACTIONS = {"send_email", "smtp_send_email"}

# Help-assistant questions: logged for rate limiting, but not the customer's AI usage
HELP_KIND = "help"

NEW_ACCOUNT_DAYS = 7
NEW_ACCOUNT_LIMITS = {"executions": 200, "ai_calls": 50, "emails": 20}


def ai_cost_per_call():
    """Estimated USD cost of one AI call (blended across providers and sizes)."""
    return float(os.getenv("AUTOFLOW_AI_COST_PER_CALL_USD", "0.01"))


class LimitReached(Exception):
    """A daily workspace limit has been reached."""


def _start_of_day():
    return datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)


def new_account_until(workspace):
    """When new-account limits end (None if they don't apply)."""
    if workspace.trusted_at is not None:
        return None
    created = workspace.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    until = created + timedelta(days=NEW_ACCOUNT_DAYS)
    return until if until > datetime.now(timezone.utc) else None


def effective_limits(workspace):
    """Today's daily limits: the workspace's own, lowered for new accounts."""
    own = {
        "executions": workspace.max_executions_per_day,
        "ai_calls": workspace.max_ai_calls_per_day,
        "emails": workspace.max_emails_per_day,
    }
    if new_account_until(workspace) is None:
        return own
    return {key: min(value, NEW_ACCOUNT_LIMITS[key]) for key, value in own.items()}


def ai_calls_since(session, workspace_id, since):
    """AI calls (step attempts plus calls outside steps) since a moment."""
    from autoflow.ai.steps import AI_ACTIONS

    in_steps = session.scalar(
        select(func.coalesce(func.sum(StepExecution.attempts), 0))
        .join(WorkflowExecution, StepExecution.execution_id == WorkflowExecution.id)
        .where(
            WorkflowExecution.workspace_id == workspace_id,
            StepExecution.started_at >= since,
            StepExecution.action.in_(AI_ACTIONS),
        )
    )
    outside = session.scalar(
        select(func.count(AIUsageEvent.id)).where(
            AIUsageEvent.workspace_id == workspace_id, AIUsageEvent.created_at >= since,
            AIUsageEvent.kind != HELP_KIND,
        )
    )
    return int(in_steps or 0) + (outside or 0)


def ai_budget(session, workspace_id):
    """This billing period's AI spend estimate against the plan's AI budget."""
    from autoflow.billing import service as billing
    from autoflow.billing import plans

    subscription = billing.get_subscription(session, workspace_id)
    plan = plans.get_plan(billing.effective_plan_name(subscription))
    start, end = billing.billing_period(subscription)
    calls = ai_calls_since(session, workspace_id, start)
    return {
        "calls": calls,
        "estimated_cost_usd": round(calls * ai_cost_per_call(), 2),
        "budget_usd": plan.get("ai_budget_usd_month"),
        "cost_per_call_usd": ai_cost_per_call(),
        "period": {"start": start, "end": end},
    }


def check_ai_budget(session, workspace):
    budget = ai_budget(session, workspace.id)
    if budget["budget_usd"] is not None and budget["estimated_cost_usd"] + budget["cost_per_call_usd"] > budget["budget_usd"]:
        raise LimitReached(
            f"This month's AI budget for your plan (about ${budget['budget_usd']:g}) is used up. "
            "AI steps resume next period, or upgrade your plan."
        )


def usage_today(session, workspace_id):
    from autoflow.ai.steps import AI_ACTIONS

    since = _start_of_day()

    executions = session.scalar(
        select(func.count(WorkflowExecution.id)).where(
            WorkflowExecution.workspace_id == workspace_id,
            WorkflowExecution.created_at >= since,
        )
    )

    step_query = (
        select(func.coalesce(func.sum(StepExecution.attempts), 0))
        .join(WorkflowExecution, StepExecution.execution_id == WorkflowExecution.id)
        .where(WorkflowExecution.workspace_id == workspace_id, StepExecution.started_at >= since)
    )

    ai_calls = session.scalar(step_query.where(StepExecution.action.in_(AI_ACTIONS)))

    emails = session.scalar(
        select(func.count(StepExecution.id))
        .join(WorkflowExecution, StepExecution.execution_id == WorkflowExecution.id)
        .where(
            WorkflowExecution.workspace_id == workspace_id,
            WorkflowExecution.mode == "live",
            StepExecution.action.in_(EMAIL_ACTIONS),
            StepExecution.status == "succeeded",
            StepExecution.finished_at >= since,
        )
    )

    # AI calls outside steps, e.g. reading scanned documents
    other_ai_calls = session.scalar(
        select(func.count(AIUsageEvent.id)).where(
            AIUsageEvent.workspace_id == workspace_id, AIUsageEvent.created_at >= since,
            AIUsageEvent.kind != HELP_KIND,
        )
    )

    return {
        "executions": executions or 0,
        "ai_calls": int(ai_calls or 0) + (other_ai_calls or 0),
        "emails": emails or 0,
    }


def use_ai_call(session, workspace, kind):
    """Check the daily AI limit and record one AI call made outside a step."""

    limit = effective_limits(workspace)["ai_calls"]
    if usage_today(session, workspace.id)["ai_calls"] >= limit:
        raise LimitReached(f"Daily limit of {limit} AI calls reached.")
    check_ai_budget(session, workspace)

    session.add(AIUsageEvent(workspace_id=workspace.id, kind=kind))
    session.commit()


def check_can_start(session, workspace):
    limit = effective_limits(workspace)["executions"]
    if usage_today(session, workspace.id)["executions"] >= limit:
        raise LimitReached(f"Daily limit of {limit} executions reached for this workspace.")


def check_can_run_step(session, workspace, action_name, mode):
    from autoflow.ai.steps import AI_ACTIONS

    if action_name not in AI_ACTIONS and not (action_name in EMAIL_ACTIONS and mode == "live"):
        return

    usage = usage_today(session, workspace.id)
    allowed = effective_limits(workspace)

    def hint(key, own):
        # Say why when the new-account limit, not the workspace's own, applies
        return " (lower limits apply to new accounts for their first week)" if allowed[key] < own else ""

    if action_name in AI_ACTIONS:
        if usage["ai_calls"] >= allowed["ai_calls"]:
            raise LimitReached(
                f"Daily limit of {allowed['ai_calls']} AI calls reached{hint('ai_calls', workspace.max_ai_calls_per_day)}."
            )
        check_ai_budget(session, workspace)

    if action_name in EMAIL_ACTIONS and usage["emails"] >= allowed["emails"]:
        raise LimitReached(
            f"Daily limit of {allowed['emails']} emails reached{hint('emails', workspace.max_emails_per_day)}."
        )


def get_workspace(session, workspace_id):
    return session.get(Workspace, workspace_id)
