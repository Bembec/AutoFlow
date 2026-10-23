"""
Creates the AutoFlow FastAPI application.

Start the development server with:  python -m autoflow.api
Interactive documentation is then available at /docs.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from autoflow import __version__, config
from autoflow.api import schemas
from autoflow.api.middleware import http_middleware
from autoflow.api.routes import (
    assistants,
    auth,
    billing,
    commerce,
    dashboard,
    data,
    help,
    insights,
    integrations,
    onboarding,
    safety,
    workflow,
    workflows,
    workspaces,
)
from autoflow.observability import init_error_tracking
from autoflow.storage import database_status, initialize_storage


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def auto_migrate():
    """Development migrates on start; staging/production migrate as a deploy step."""
    default = "true" if config.ENVIRONMENT == "development" else "false"
    return os.getenv("AUTOFLOW_AUTO_MIGRATE", default).lower() == "true"


@asynccontextmanager
async def lifespan(app):
    config.check_deployment_settings()
    init_error_tracking("api")

    if auto_migrate():
        initialize_storage()

    yield


def create_app():
    """Build the API application with all routes registered."""

    app = FastAPI(
        title="AutoFlow API",
        version=__version__,
        lifespan=lifespan,
        # No public API docs in production
        docs_url=None if config.ENVIRONMENT == "production" else "/docs",
        redoc_url=None,
    )

    app.middleware("http")(http_middleware)

    if config.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.CORS_ORIGINS,
            allow_methods=["*"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
        )

    @app.get("/health", response_model=schemas.Health, tags=["system"])
    def health():
        """Liveness: the process is up."""
        return {"status": "ok", "version": __version__}

    @app.get("/ready", tags=["system"])
    def ready():
        """Readiness: the database answers and its schema is up to date."""

        status = database_status()
        code = 200 if status["database"] == "ok" and status["schema"] == "current" else 503
        return JSONResponse({**status, "version": __version__}, status_code=code)

    app.include_router(auth.router)
    app.include_router(workspaces.router)
    app.include_router(workflow.router)
    app.include_router(workflows.router)
    app.include_router(workflows.workspace_router)
    app.include_router(integrations.router)
    app.include_router(integrations.workspace_router)
    app.include_router(dashboard.router)
    app.include_router(onboarding.router)
    app.include_router(insights.router)
    app.include_router(safety.router)
    app.include_router(help.router)
    app.include_router(assistants.router)
    app.include_router(billing.router)
    app.include_router(data.router)
    app.include_router(commerce.router)

    return app


app = create_app()
