"""
Per-workspace safety limits, counted per UTC day.

- executions started
- AI model calls (AI action attempts, test and live: both cost money)
- emails sent (live sends that succeeded)

Hitting a limit stops the run or step with a clear message instead of
letting a runaway workflow spend money or spam customers.
"""

from datetime import datetime, time, timezone

from sqlalchemy import func, select

from autoflow.storage.models import StepExecution, WorkflowExecution, Workspace


EMAIL_ACTIONS = {"send_email", "smtp_send_email"}


class LimitReached(Exception):
    """A daily workspace limit has been reached."""


def _start_of_day():
    return datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)


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

    return {"executions": executions or 0, "ai_calls": int(ai_calls or 0), "emails": emails or 0}


def check_can_start(session, workspace):
    if usage_today(session, workspace.id)["executions"] >= workspace.max_executions_per_day:
        raise LimitReached(
            f"Daily limit of {workspace.max_executions_per_day} executions reached for this workspace."
        )


def check_can_run_step(session, workspace, action_name, mode):
    from autoflow.ai.steps import AI_ACTIONS

    if action_name not in AI_ACTIONS and not (action_name in EMAIL_ACTIONS and mode == "live"):
        return

    usage = usage_today(session, workspace.id)

    if action_name in AI_ACTIONS and usage["ai_calls"] >= workspace.max_ai_calls_per_day:
        raise LimitReached(f"Daily limit of {workspace.max_ai_calls_per_day} AI calls reached.")

    if action_name in EMAIL_ACTIONS and usage["emails"] >= workspace.max_emails_per_day:
        raise LimitReached(f"Daily limit of {workspace.max_emails_per_day} emails reached.")


def get_workspace(session, workspace_id):
    return session.get(Workspace, workspace_id)
