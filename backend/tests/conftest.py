"""Shared pytest setup: keep test data out of the real data folder."""

import os
import tempfile

# Must be set before any autoflow module is imported
os.environ.setdefault("AUTOFLOW_DATA_DIR", tempfile.mkdtemp(prefix="autoflow-test-"))
os.environ["AI_CLASSIFICATION_ENABLED"] = "false"
os.environ["EMAIL_SEND_ENABLED"] = "false"


import sqlite3

import pytest


@pytest.fixture(autouse=True)
def clean_database():
    """Give every test empty tables."""

    from autoflow.storage import initialize_storage
    from autoflow.storage.database import database_path

    initialize_storage()

    with sqlite3.connect(database_path) as connection:
        for table in ("customers", "workflow_runs", "approvals"):
            connection.execute(f"DELETE FROM {table}")

    yield
