"""Shared pytest setup: an isolated database and API helpers."""

import os
import tempfile

# Must be set before any autoflow module is imported
os.environ.setdefault("AUTOFLOW_DATA_DIR", tempfile.mkdtemp(prefix="autoflow-test-"))
os.environ["AI_CLASSIFICATION_ENABLED"] = "false"
os.environ["EMAIL_SEND_ENABLED"] = "false"

from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from autoflow.api.app import create_app  # noqa: E402
from autoflow.storage import initialize_storage  # noqa: E402
from autoflow.storage.db import Base, engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    # Running the real migrations also tests them
    initialize_storage()


@pytest.fixture(autouse=True)
def clean_database():
    """Give every test empty tables."""

    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())

    yield


@pytest.fixture
def no_external_calls():
    """Stop the workflow from calling real external services."""

    with (
        patch("autoflow.pipeline.fetch_eur_to_usd", return_value=(1.1, "2026-10-21")),
        patch("autoflow.pipeline.sync_customers_to_airtable") as airtable,
    ):
        yield airtable


@pytest.fixture
def client(no_external_calls):
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def signup(client):
    """Register and log in a user; return (auth headers, workspace id)."""

    def _signup(email="owner@example.com", name="Owner", password="correct-horse"):
        client.post(
            "/auth/register",
            json={"email": email, "name": name, "password": password},
        )
        token = client.post(
            "/auth/login", json={"email": email, "password": password}
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        workspace_id = client.get("/me", headers=headers).json()["workspaces"][0]["id"]
        return headers, workspace_id

    return _signup
