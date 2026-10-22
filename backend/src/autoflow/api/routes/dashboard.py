"""Dashboard summary: activity, approvals and time saved per workspace."""

from datetime import timedelta

from fastapi import APIRouter
from sqlalchemy import func, select

from autoflow.api.deps import Session, ViewerAccess
from autoflow.engine import limits
from autoflow.storage.db import utc_now
from autoflow.storage.models import Approval, Workflow, WorkflowExecution


router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["dashboard"])


@router.get("/dashboard")
def dashboard(membership: ViewerAccess, session: Session):
    workspace_id = membership.workspace_id
    workspace = limits.get_workspace(session, workspace_id)
    since_day = limits._start_of_day()
    since_month = utc_now() - timedelta(days=30)

    workflows = session.scalars(
        select(Workflow).where(Workflow.workspace_id == workspace_id, Workflow.status != "archived")
    ).all()

    today_by_status = dict(session.execute(
        select(WorkflowExecution.status, func.count())
        .where(WorkflowExecution.workspace_id == workspace_id, WorkflowExecution.created_at >= since_day)
        .group_by(WorkflowExecution.status)
    ).all())

    # Time saved = successful live runs × the owner's minutes-per-run estimate
    succeeded = dict(session.execute(
        select(WorkflowExecution.workflow_id, func.count())
        .where(
            WorkflowExecution.workspace_id == workspace_id,
            WorkflowExecution.mode == "live",
            WorkflowExecution.status == "succeeded",
            WorkflowExecution.created_at >= since_month,
        )
        .group_by(WorkflowExecution.workflow_id)
    ).all())

    per_workflow = [
        {
            "id": workflow.id,
            "name": workflow.name,
            "status": workflow.status,
            "runs_succeeded_30d": succeeded.get(workflow.id, 0),
            "minutes_saved_30d": succeeded.get(workflow.id, 0) * workflow.minutes_saved_per_run,
        }
        for workflow in workflows
    ]

    names = {workflow.id: workflow.name for workflow in workflows}
    recent = session.scalars(
        select(WorkflowExecution)
        .where(WorkflowExecution.workspace_id == workspace_id)
        .order_by(WorkflowExecution.id.desc())
        .limit(10)
    ).all()

    pending_approvals = session.scalar(
        select(func.count(Approval.id)).where(
            Approval.workspace_id == workspace_id, Approval.status == "pending"
        )
    )

    return {
        "automation_paused": workspace.automation_paused,
        "paused_reason": workspace.paused_reason,
        "workflows": {
            "total": len(workflows),
            "active": sum(w.status == "active" for w in workflows),
            "paused": sum(w.status == "paused" for w in workflows),
        },
        "executions_today": today_by_status,
        "pending_approvals": pending_approvals or 0,
        "minutes_saved_30d": sum(item["minutes_saved_30d"] for item in per_workflow),
        "per_workflow": per_workflow,
        "recent_executions": [
            {
                "id": execution.id,
                "workflow_id": execution.workflow_id,
                "workflow_name": names.get(execution.workflow_id, f"Workflow {execution.workflow_id}"),
                "mode": execution.mode,
                "status": execution.status,
                "created_at": execution.created_at,
            }
            for execution in recent
        ],
        "usage_today": limits.usage_today(session, workspace_id),
        "limits": {
            "executions": workspace.max_executions_per_day,
            "ai_calls": workspace.max_ai_calls_per_day,
            "emails": workspace.max_emails_per_day,
        },
    }
