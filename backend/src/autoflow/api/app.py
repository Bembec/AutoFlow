"""
Creates the AutoFlow FastAPI application.

Start the development server with:  python -m autoflow.api
Interactive documentation is then available at /docs.
"""

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Query

from autoflow import __version__, approvals
from autoflow.api import schemas
from autoflow.pipeline import run as run_pipeline
from autoflow.storage import approvals as approval_store
from autoflow.storage import database, initialize_storage


Category = Literal["Sales", "Support", "Other"]
ApprovalStatus = Literal["pending", "approved", "rejected", "sent", "failed"]
ApprovalKind = Literal["classification", "email"]


@asynccontextmanager
async def lifespan(app):
    # Make sure the tables exist before the first request
    initialize_storage()
    yield


def create_app():
    """Build the API application with all routes registered."""

    app = FastAPI(
        title="AutoFlow API",
        version=__version__,
        lifespan=lifespan,
    )

    @app.get("/health", response_model=schemas.Health, tags=["system"])
    def health():
        return {"status": "ok", "version": __version__}

    @app.get(
        "/customers",
        response_model=list[schemas.CustomerSummary],
        tags=["customers"],
    )
    def list_customers(category: Category | None = None):
        return database.get_all_customers(category)

    @app.get(
        "/customers/{customer_row_id}",
        response_model=schemas.CustomerDetail,
        tags=["customers"],
    )
    def get_customer(customer_row_id: int):
        customer = database.get_customer(customer_row_id)

        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")

        return customer

    @app.get(
        "/workflow-runs",
        response_model=list[schemas.WorkflowRun],
        tags=["workflow runs"],
    )
    def list_workflow_runs(limit: int = Query(10, ge=1, le=100)):
        return database.get_workflow_runs(limit)

    @app.post(
        "/workflow-runs",
        response_model=schemas.WorkflowRunResult,
        status_code=201,
        tags=["workflow runs"],
    )
    def start_workflow_run():
        # Runs without a terminal: decisions are queued as approvals
        return run_pipeline(interactive=False)

    @app.get(
        "/approvals",
        response_model=list[schemas.Approval],
        tags=["approvals"],
    )
    def list_approvals(
        status: ApprovalStatus | None = None,
        kind: ApprovalKind | None = None,
    ):
        return approval_store.list_approvals(status, kind)

    @app.get(
        "/approvals/{approval_id}",
        response_model=schemas.Approval,
        tags=["approvals"],
    )
    def get_approval(approval_id: int):
        approval = approval_store.get_approval(approval_id)

        if approval is None:
            raise HTTPException(status_code=404, detail="Approval not found")

        return approval

    @app.post(
        "/approvals/{approval_id}/approve",
        response_model=schemas.Approval,
        tags=["approvals"],
    )
    def approve(approval_id: int, decision: schemas.ApprovalDecision | None = None):
        category = decision.category if decision else None
        return _decide(lambda: approvals.approve(approval_id, category))

    @app.post(
        "/approvals/{approval_id}/reject",
        response_model=schemas.Approval,
        tags=["approvals"],
    )
    def reject(approval_id: int):
        return _decide(lambda: approvals.reject(approval_id))

    return app


def _decide(action):
    """Translate approval errors into HTTP responses."""

    try:
        return action()
    except approvals.ApprovalNotFound:
        raise HTTPException(status_code=404, detail="Approval not found")
    except approvals.ApprovalConflict as error:
        raise HTTPException(status_code=409, detail=str(error))


app = create_app()
