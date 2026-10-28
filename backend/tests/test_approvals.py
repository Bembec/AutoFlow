from unittest.mock import patch

import pytest


def fake_ai(message):
    # Pretend the AI calls everything Sales
    return {"category": "Sales", "reason": "Mentions buying."}


@pytest.fixture
def workspace(client, signup):
    """A workspace whose workflow has run once with (fake) AI enabled."""

    headers, workspace_id = signup()
    base = f"/workspaces/{workspace_id}"

    with patch("luphina.pipeline.classify_with_ai", side_effect=fake_ai):
        client.post(f"{base}/workflow-runs", headers=headers)

    return client, headers, base


def pending(workspace, kind, email):
    client, headers, base = workspace
    approvals = client.get(
        f"{base}/approvals",
        params={"status": "pending", "kind": kind},
        headers=headers,
    ).json()
    return next(a for a in approvals if a["customer_email"] == email)


def test_run_queues_approvals_instead_of_acting(workspace):
    client, headers, base = workspace

    queued = client.get(f"{base}/approvals", params={"status": "pending"}, headers=headers).json()
    assert sum(a["kind"] == "classification" for a in queued) == 4
    assert sum(a["kind"] == "email" for a in queued) == 4

    # Running again refreshes pending approvals instead of duplicating them
    with patch("luphina.pipeline.classify_with_ai", side_effect=fake_ai):
        client.post(f"{base}/workflow-runs", headers=headers)

    queued = client.get(f"{base}/approvals", params={"status": "pending"}, headers=headers).json()
    assert len(queued) == 8


def test_email_waits_for_classification_review(workspace):
    client, headers, base = workspace
    email_approval = pending(workspace, "email", "james@example.com")

    response = client.post(f"{base}/approvals/{email_approval['id']}/approve", headers=headers)

    assert response.status_code == 409


def test_correction_updates_customer_and_email(workspace):
    client, headers, base = workspace
    review = pending(workspace, "classification", "james@example.com")

    response = client.post(
        f"{base}/approvals/{review['id']}/approve",
        json={"category": "Support"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["decision"]["category"] == "Support"
    assert response.json()["decided_by_user_id"] is not None

    customers = client.get(
        f"{base}/customers", params={"category": "Support"}, headers=headers
    ).json()
    james = next(c for c in customers if c["email"] == "james@example.com")
    assert james["classification_source"] == "Human Correction"

    email_approval = pending(workspace, "email", "james@example.com")
    assert email_approval["payload"]["subject"] == "We received your support request"


def test_approved_email_is_sent_exactly_once(workspace):
    client, headers, base = workspace
    review = pending(workspace, "classification", "ada@example.com")
    client.post(f"{base}/approvals/{review['id']}/approve", headers=headers)
    email_approval = pending(workspace, "email", "ada@example.com")

    with patch("luphina.approvals.send_email", return_value=True) as send:
        first = client.post(f"{base}/approvals/{email_approval['id']}/approve", headers=headers)
        second = client.post(f"{base}/approvals/{email_approval['id']}/approve", headers=headers)

    assert first.json()["status"] == "sent"
    assert second.status_code == 409
    send.assert_called_once()


def test_reject_sends_nothing(workspace):
    client, headers, base = workspace
    email_approval = pending(workspace, "email", "sara@example.com")

    with patch("luphina.approvals.send_email") as send:
        response = client.post(
            f"{base}/approvals/{email_approval['id']}/reject", headers=headers
        )

    assert response.json()["status"] == "rejected"
    send.assert_not_called()


def test_unknown_approval_returns_404(workspace):
    client, headers, base = workspace

    assert client.post(f"{base}/approvals/999/approve", headers=headers).status_code == 404


def test_other_workspace_cannot_decide_approvals(workspace, signup):
    client, _, base = workspace
    email_approval = pending(workspace, "email", "sara@example.com")
    other_headers, other_workspace = signup("intruder@example.com")

    # Neither through the victim's workspace path...
    assert client.post(
        f"{base}/approvals/{email_approval['id']}/reject", headers=other_headers
    ).status_code == 404

    # ...nor by using the approval id inside their own workspace
    assert client.post(
        f"/workspaces/{other_workspace}/approvals/{email_approval['id']}/reject",
        headers=other_headers,
    ).status_code == 404
