"""Workflow execution history, always scoped to one workspace."""

from sqlalchemy import select

from autoflow.storage.models import WorkflowRun


def record_workflow_run(session, workspace_id, customer_count, ai_enabled, status="SUCCESS"):
    """Save a summary of one AutoFlow execution and return its id."""

    workflow_run = WorkflowRun(
        workspace_id=workspace_id,
        customer_count=customer_count,
        ai_enabled=ai_enabled,
        status=status,
    )
    session.add(workflow_run)
    session.flush()

    print("Workflow run recorded in the database.")
    return workflow_run.id


def list_workflow_runs(session, workspace_id, limit=10):
    """Return the most recent executions, newest first."""

    return session.scalars(
        select(WorkflowRun)
        .where(WorkflowRun.workspace_id == workspace_id)
        .order_by(WorkflowRun.id.desc())
        .limit(limit)
    ).all()
