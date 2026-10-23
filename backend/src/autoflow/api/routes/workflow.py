"""
Workspace data: customers, workflow runs and approvals.

Every route is nested under /workspaces/{workspace_id} and checks the
caller's role in that workspace before touching its data.
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from autoflow import approvals, audit
from autoflow.api import schemas
from autoflow.api.deps import MemberAccess, Session, ViewerAccess
from autoflow.engine.limits import get_workspace
from autoflow.pipeline import run_for_workspace
from autoflow.storage import approvals as approval_store
from autoflow.storage import customers as customer_store
from autoflow.storage import workflow_runs as run_store


router = APIRouter(prefix="/workspaces/{workspace_id}")

ApprovalStatus = Literal["pending", "approved", "rejected", "sent", "failed", "cancelled"]
ApprovalKind = Literal["classification", "email", "step"]


@router.get(
    "/customers",
    response_model=list[schemas.CustomerSummary],
    tags=["customers"],
)
def list_customers(
    membership: ViewerAccess,
    session: Session,
    category: schemas.Category | None = None,
):
    return customer_store.list_customers(session, membership.workspace_id, category)


@router.get(
    "/customers/{customer_row_id}",
    response_model=schemas.CustomerDetail,
    tags=["customers"],
)
def get_customer(customer_row_id: int, membership: ViewerAccess, session: Session):
    customer = customer_store.get_customer(
        session, membership.workspace_id, customer_row_id
    )

    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    return customer


@router.get(
    "/workflow-runs",
    response_model=list[schemas.WorkflowRun],
    tags=["workflow runs"],
)
def list_workflow_runs(
    membership: ViewerAccess,
    session: Session,
    limit: int = Query(10, ge=1, le=100),
):
    return run_store.list_workflow_runs(session, membership.workspace_id, limit)


@router.post(
    "/workflow-runs",
    response_model=schemas.WorkflowRunResult,
    status_code=201,
    tags=["workflow runs"],
)
def start_workflow_run(membership: MemberAccess, session: Session):
    if get_workspace(session, membership.workspace_id).automation_paused:
        raise HTTPException(status_code=409, detail="Automations are stopped for this workspace.")

    # Runs without a terminal: decisions are queued as approvals
    return run_for_workspace(session, membership.workspace_id, interactive=False)


@router.get(
    "/approvals",
    response_model=list[schemas.Approval],
    tags=["approvals"],
)
def list_approvals(
    membership: ViewerAccess,
    session: Session,
    status: ApprovalStatus | None = None,
    kind: ApprovalKind | None = None,
):
    return approval_store.list_approvals(
        session, membership.workspace_id, status, kind
    )


@router.get(
    "/approvals/{approval_id}",
    response_model=schemas.Approval,
    tags=["approvals"],
)
def get_approval(approval_id: int, membership: ViewerAccess, session: Session):
    approval = approval_store.get_approval(
        session, membership.workspace_id, approval_id
    )

    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")

    return approval


@router.post(
    "/approvals/{approval_id}/approve",
    response_model=schemas.Approval,
    tags=["approvals"],
)
def approve(
    approval_id: int,
    membership: MemberAccess,
    session: Session,
    decision: schemas.ApprovalDecision | None = None,
):
    category = decision.category if decision else None
    output = decision.output if decision else None

    approval = _decide(lambda: approvals.approve(
        session,
        membership.workspace_id,
        approval_id,
        category,
        user_id=membership.user_id,
        output=output,
    ))
    audit.for_member(membership, session, "approval.approved", target=f"approval {approval_id}",
                     details={"corrected": bool(category or output)})
    return approval


@router.post(
    "/approvals/{approval_id}/reject",
    response_model=schemas.Approval,
    tags=["approvals"],
)
def reject(approval_id: int, membership: MemberAccess, session: Session):
    approval = _decide(lambda: approvals.reject(
        session,
        membership.workspace_id,
        approval_id,
        user_id=membership.user_id,
    ))
    audit.for_member(membership, session, "approval.rejected", target=f"approval {approval_id}")
    return approval


def _decide(action):
    """Translate approval errors into HTTP responses."""

    try:
        return action()
    except approvals.ApprovalNotFound:
        raise HTTPException(status_code=404, detail="Approval not found")
    except approvals.ApprovalConflict as error:
        raise HTTPException(status_code=409, detail=str(error))
