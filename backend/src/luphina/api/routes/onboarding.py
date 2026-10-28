"""Getting-started checklist: what a new shop still has to do to go live.

Every step is worked out from data the workspace already has, so the
checklist can't drift from reality (deleting the email connection
un-ticks that step again).
"""

from fastapi import APIRouter
from sqlalchemy import exists, select

from luphina.api.deps import Session, ViewerAccess
from luphina.engine import limits
from luphina.storage.models import (
    Connection,
    WebhookEndpoint,
    Workflow,
    WorkflowExecution,
    WorkflowVersion,
)


router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["onboarding"])

# Order matters: it's the order the checklist shows
STEPS = ("business", "email", "template", "test", "publish", "live")

# Test runs that reached the end, or stopped at an approval (which is the
# expected outcome for templates that email customers)
TEST_PASSED = ("succeeded", "waiting_approval")


@router.get("/onboarding")
def onboarding(membership: ViewerAccess, session: Session):
    workspace_id = membership.workspace_id
    workspace = limits.get_workspace(session, workspace_id)

    def any_row(query) -> bool:
        return bool(session.scalar(select(exists(query))))

    current_workflows = select(Workflow.id).where(
        Workflow.workspace_id == workspace_id, Workflow.status != "archived"
    )
    done = {
        "business": bool(workspace.business_name),
        "email": any_row(
            select(Connection.id).where(
                Connection.workspace_id == workspace_id,
                Connection.provider == "smtp",
                Connection.status == "active",
            )
        ),
        "template": any_row(current_workflows),
        "test": any_row(
            select(WorkflowExecution.id).where(
                WorkflowExecution.workspace_id == workspace_id,
                WorkflowExecution.mode == "test",
                WorkflowExecution.status.in_(TEST_PASSED),
            )
        ),
        "publish": any_row(
            select(WorkflowVersion.id)
            .join(Workflow, Workflow.id == WorkflowVersion.workflow_id)
            .where(
                Workflow.workspace_id == workspace_id,
                Workflow.status == "active",
                WorkflowVersion.state == "published",
            )
        ),
        # The store has talked to us, or something already ran for real
        "live": any_row(
            select(WebhookEndpoint.id).where(
                WebhookEndpoint.workspace_id == workspace_id,
                WebhookEndpoint.last_called_at.is_not(None),
            )
        )
        or any_row(
            select(WorkflowExecution.id).where(
                WorkflowExecution.workspace_id == workspace_id,
                WorkflowExecution.mode == "live",
            )
        ),
    }

    completed = sum(done.values())
    return {
        "steps": [{"id": step, "done": done[step]} for step in STEPS],
        "completed": completed,
        "total": len(STEPS),
        "complete": completed == len(STEPS),
    }
