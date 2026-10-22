from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from autoflow.api.app import create_app


@pytest.fixture
def client():
    # Avoid calling external services during tests
    with (
        patch(
            "autoflow.pipeline.fetch_eur_to_usd",
            return_value=(1.1, "2026-10-21"),
        ),
        patch("autoflow.pipeline.sync_customers_to_airtable"),
        TestClient(create_app()) as test_client,
    ):
        yield test_client


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_run_workflow_then_read_results(client):
    response = client.post("/workflow-runs")

    assert response.status_code == 201
    result = response.json()
    assert result["customer_count"] == 4
    assert result["categories"] == {"Sales": 2, "Support": 1, "Other": 1}
    assert result["emails"] == []

    runs = client.get("/workflow-runs", params={"limit": 1}).json()
    assert runs[0]["id"] == result["run_id"]

    sales = client.get("/customers", params={"category": "Sales"}).json()
    assert {customer["email"] for customer in sales} >= {
        "ada@example.com",
        "david@example.com",
    }

    detail = client.get(f"/customers/{sales[0]['id']}").json()
    assert detail["quote_usd"] == "110.00"


def test_unknown_customer_returns_404(client):
    assert client.get("/customers/999999").status_code == 404


def test_invalid_category_is_rejected(client):
    assert client.get("/customers", params={"category": "Spam"}).status_code == 422
