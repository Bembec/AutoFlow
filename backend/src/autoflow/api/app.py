"""
Creates the AutoFlow FastAPI application.

Start the development server with:  python -m autoflow.api
Interactive documentation is then available at /docs.
"""

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Query

from autoflow import __version__
from autoflow.api import schemas
from autoflow.pipeline import run as run_pipeline
from autoflow.storage import database


Category = Literal["Sales", "Support", "Other"]


@asynccontextmanager
async def lifespan(app):
    # Make sure the tables exist before the first request
    database.initialize_database()
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
        # Runs without a terminal: AI results stay unreviewed, no email is sent
        return run_pipeline(interactive=False)

    return app


app = create_app()
