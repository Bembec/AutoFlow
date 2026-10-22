from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from autoflow.api.app import create_app


def fake_ai(message):
    # Pretend the AI calls everything Sales
    return {"category": "Sales", "reason": "Mentions buying."}


@pytest.fixture
def client():
    with (
        patch("autoflow.pipeline.fetch_eur_to_usd", return_value=(1.1, "2026-10-21")),
        patch("autoflow.pipeline.sync_customers_to_airtable"),
        patch("autoflow.pipeline.classify_with_ai", side_effect=fake_ai),
        TestClient(create_app()) as test_client,
    ):
        yield test_client


def pending(client, kind, email):
    approvals = client.get(
        "/approvals", params={"status": "pending", "kind": kind}
    ).json()
    return next(a for a in approvals if a["customer_email"] == email)


def test_run_queues_approvals_instead_of_acting(client):
    client.post("/workflow-runs")

    queued = client.get("/approvals", params={"status": "pending"}).json()
    assert sum(a["kind"] == "classification" for a in queued) == 4
    assert sum(a["kind"] == "email" for a in queued) == 4

    # Running again refreshes pending approvals instead of duplicating them
    client.post("/workflow-runs")
    assert len(client.get("/approvals", params={"status": "pending"}).json()) == 8


def test_email_waits_for_classification_review(client):
    client.post("/workflow-runs")
    email_approval = pending(client, "email", "james@example.com")

    response = client.post(f"/approvals/{email_approval['id']}/approve")

    assert response.status_code == 409


def test_correction_updates_customer_and_email(client):
    client.post("/workflow-runs")
    review = pending(client, "classification", "james@example.com")

    response = client.post(
        f"/approvals/{review['id']}/approve", json={"category": "Support"}
    )

    assert response.status_code == 200
    assert response.json()["decision"]["category"] == "Support"

    customers = client.get("/customers", params={"category": "Support"}).json()
    james = next(c for c in customers if c["email"] == "james@example.com")
    assert james["classification_source"] == "Human Correction"

    email_approval = pending(client, "email", "james@example.com")
    assert email_approval["payload"]["subject"] == "We received your support request"


def test_approved_email_is_sent_exactly_once(client):
    client.post("/workflow-runs")
    review = pending(client, "classification", "ada@example.com")
    client.post(f"/approvals/{review['id']}/approve")
    email_approval = pending(client, "email", "ada@example.com")

    with patch("autoflow.approvals.send_email", return_value=True) as send:
        first = client.post(f"/approvals/{email_approval['id']}/approve")
        second = client.post(f"/approvals/{email_approval['id']}/approve")

    assert first.json()["status"] == "sent"
    assert second.status_code == 409
    send.assert_called_once()


def test_reject_sends_nothing(client):
    client.post("/workflow-runs")
    email_approval = pending(client, "email", "sara@example.com")

    with patch("autoflow.approvals.send_email") as send:
        response = client.post(f"/approvals/{email_approval['id']}/reject")

    assert response.json()["status"] == "rejected"
    send.assert_not_called()


def test_unknown_approval_returns_404(client):
    assert client.post("/approvals/999/approve").status_code == 404
