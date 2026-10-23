from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("autoflow.engine.executor.sleep"):
        yield


def progress(client, headers, base):
    response = client.get(f"{base}/onboarding", headers=headers)
    assert response.status_code == 200
    body = response.json()
    return {step["id"]: step["done"] for step in body["steps"]}, body


def test_checklist_follows_the_shop_through_setup(client, signup):
    headers, workspace_id = signup()
    base = f"/workspaces/{workspace_id}"

    steps, body = progress(client, headers, base)
    assert list(steps) == ["business", "email", "template", "test", "publish", "live"]
    assert not any(steps.values())
    assert body == {**body, "completed": 0, "total": 6, "complete": False}

    client.patch(f"{base}/business", json={"business_name": "Mug & Bean Ltd"}, headers=headers)
    connection = client.post(f"{base}/connections", json={
        "provider": "smtp", "name": "mailbox",
        "config": {"host": "smtp.example.com", "username": "shop@example.com", "from_address": "shop@example.com"},
        "secrets": {"password": "app-password-123"},
    }, headers=headers).json()
    workflow = client.post(
        f"{base}/workflows/from-template", json={"template": "shopify-order-to-invoice"}, headers=headers
    ).json()
    steps, _ = progress(client, headers, base)
    assert steps == {**steps, "business": True, "email": True, "template": True, "test": False}

    run = client.post(f"{base}/workflows/{workflow['id']}/executions", json={"mode": "test"}, headers=headers).json()
    assert run["status"] in ("succeeded", "waiting_approval")
    client.post(f"{base}/workflows/{workflow['id']}/publish", headers=headers)
    steps, _ = progress(client, headers, base)
    assert steps["test"] and steps["publish"] and not steps["live"]

    client.post(f"{base}/workflows/{workflow['id']}/executions", json={"mode": "live"}, headers=headers)
    steps, body = progress(client, headers, base)
    assert all(steps.values()) and body["complete"]

    # Progress reflects the current state, not history
    client.delete(f"{base}/connections/{connection['id']}", headers=headers)
    client.post(f"{base}/workflows/{workflow['id']}/pause", headers=headers)
    steps, body = progress(client, headers, base)
    assert not steps["email"] and not steps["publish"] and body["completed"] == 4


def test_checklist_is_per_workspace(client, signup):
    owner_headers, owner_ws = signup()
    client.post(
        f"/workspaces/{owner_ws}/workflows/from-template",
        json={"template": "shopify-order-to-invoice"},
        headers=owner_headers,
    )
    other_headers, other_ws = signup(email="other@example.com")

    steps, _ = progress(client, other_headers, f"/workspaces/{other_ws}")
    assert not steps["template"]
    assert client.get(f"/workspaces/{owner_ws}/onboarding", headers=other_headers).status_code in (403, 404)
