"""Assistants page: ready-made AI assistant roles and how the active ones are doing."""

from datetime import timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from autoflow import features
from autoflow.api.deps import Session, ViewerAccess
from autoflow.engine import limits
from autoflow.engine.templates import TEMPLATES
from autoflow.engine.templates_assistants import CATEGORY, role_summary
from autoflow.storage.db import utc_now
from autoflow.storage.models import Approval, Workflow, WorkflowExecution

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["assistants"])


@router.get("/assistants")
def assistants(membership: ViewerAccess, session: Session):
    workspace = limits.get_workspace(session, membership.workspace_id)
    if not features.enabled("ai_assistants", workspace):
        raise HTTPException(status_code=403, detail="AI assistants are not switched on for this workspace yet.")

    roles = [t for t in TEMPLATES.values() if t.get("category") == CATEGORY]
    installed = session.scalars(select(Workflow).where(
        Workflow.workspace_id == workspace.id,
        Workflow.status != "archived",
        Workflow.source_template.in_([role["slug"] for role in roles]),
    )).all()
    week_ago = utc_now() - timedelta(days=7)

    def stats(workflow):
        by_status = dict(session.execute(
            select(WorkflowExecution.status, func.count()).where(
                WorkflowExecution.workflow_id == workflow.id,
                WorkflowExecution.mode == "live",
                WorkflowExecution.created_at >= week_ago,
            ).group_by(WorkflowExecution.status)
        ).all())
        waiting = session.scalar(select(func.count(Approval.id)).join(
            WorkflowExecution, WorkflowExecution.id == Approval.execution_id
        ).where(WorkflowExecution.workflow_id == workflow.id, Approval.status == "pending"))
        return {
            "handled_7d": sum(by_status.values()),
            "succeeded_7d": by_status.get("succeeded", 0),
            "failed_7d": by_status.get("failed", 0) + by_status.get("needs_attention", 0),
            "waiting_approval": waiting or 0,
        }

    return {
        "roles": [
            {"slug": role["slug"], "name": role["name"], "description": role["description"],
             "requires": role.get("requires", []), **role_summary(role)}
            for role in roles
        ],
        "active": [
            {"workflow_id": workflow.id, "name": workflow.name, "role": workflow.source_template,
             "status": workflow.status, "live": any(v.state == "published" for v in workflow.versions),
             **stats(workflow)}
            for workflow in installed
        ],
    }
