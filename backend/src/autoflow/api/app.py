"""
Creates the AutoFlow FastAPI application.

Start the development server with:  python -m autoflow.api
Interactive documentation is then available at /docs.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from autoflow import __version__
from autoflow.api import schemas
from autoflow.api.routes import auth, billing, dashboard, integrations, workflow, workflows, workspaces
from autoflow.storage import initialize_storage


@asynccontextmanager
async def lifespan(app):
    # Bring the database schema up to date before the first request
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

    app.include_router(auth.router)
    app.include_router(workspaces.router)
    app.include_router(workflow.router)
    app.include_router(workflows.router)
    app.include_router(workflows.workspace_router)
    app.include_router(integrations.router)
    app.include_router(integrations.workspace_router)
    app.include_router(dashboard.router)
    app.include_router(billing.router)

    return app


app = create_app()
