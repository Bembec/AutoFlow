from datetime import timedelta

from sqlalchemy import select, update

from autoflow.storage.db import session_scope, utc_now
from autoflow.storage.models import Workflow, WorkflowExecution, WorkflowVersion


def add_runs(workflow_id, statuses, days_ago=1):
    """Insert finished live runs directly (no engine needed)."""
    with session_scope() as session:
        workflow = session.get(Workflow, workflow_id)
        version = session.scalars(select(WorkflowVersion).where(WorkflowVersion.workflow_id == workflow_id)).first()
        for status in statuses:
            session.add(WorkflowExecution(
                workspace_id=workflow.workspace_id, workflow_id=workflow_id, version_id=version.id,
                mode="live", status=status, trigger_payload={}, created_at=utc_now() - timedelta(days=days_ago),
            ))


def get(client, headers, base):
    response = client.get(f"{base}/insights", headers=headers)
    assert response.status_code == 200
    return response.json()


def ids(body):
    return [item["id"] for item in body["suggestions"]]


def test_new_shop_is_offered_the_invoice_template(client, signup):
    headers, workspace_id = signup()
    body = get(client, headers, f"/workspaces/{workspace_id}")

    assert body["last_30_days"] == {
        "live_runs": 0, "succeeded": 0, "failed": 0, "success_rate": None, "minutes_saved": 0, "money_saved": None,
    }
    assert body["weekly_minutes_saved"] == [0] * 8
    assert ids(body) == ["template-order-invoice"]
    assert body["suggestions"][0]["template"] == "shopify-order-to-invoice"


def test_savings_money_and_follow_up_suggestions(client, signup):
    headers, workspace_id = signup()
    base = f"/workspaces/{workspace_id}"
    workflow = client.post(
        f"{base}/workflows/from-template", json={"template": "shopify-order-to-invoice"}, headers=headers
    ).json()
    client.post(f"{base}/workflows/{workflow['id']}/publish", headers=headers)
    client.patch(f"{base}/workflows/{workflow['id']}", json={"minutes_saved_per_run": 6}, headers=headers)

    add_runs(workflow["id"], ["succeeded"] * 10)
    add_runs(workflow["id"], ["succeeded"] * 2, days_ago=20)
    add_runs(workflow["id"], ["succeeded"], days_ago=45)  # counts for the trend only

    body = get(client, headers, base)
    month = body["last_30_days"]
    assert month["succeeded"] == 12 and month["minutes_saved"] == 72 and month["money_saved"] is None
    assert month["success_rate"] == 1.0
    assert sum(body["weekly_minutes_saved"]) == 78 and body["weekly_minutes_saved"][-1] == 60

    # The order template is installed: next come carts and reviews; alerts and business details are missing
    assert ids(body) == ["alerts", "business", "template-abandoned-cart", "template-reviews"]

    response = client.put(f"{base}/insights/time-value", json={"per_hour": 30, "currency": "EUR"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["time_value"] == {"per_hour": 30, "currency": "EUR"}
    assert body["last_30_days"]["money_saved"] == 36.0
    assert body["per_workflow"][0]["money_saved_30d"] == 36.0

    assert client.put(f"{base}/insights/time-value", json={"per_hour": 30, "currency": "euro"}, headers=headers).status_code == 422


def test_problem_workflows_come_first(client, signup):
    headers, workspace_id = signup()
    base = f"/workspaces/{workspace_id}"
    failing = client.post(
        f"{base}/workflows/from-template", json={"template": "woocommerce-order-to-invoice"}, headers=headers
    ).json()
    client.post(f"{base}/workflows/{failing['id']}/publish", headers=headers)
    add_runs(failing["id"], ["succeeded"] * 6 + ["failed", "needs_attention"])
    unfinished = client.post(
        f"{base}/workflows/from-template", json={"template": "review-reply-assistant"}, headers=headers
    ).json()

    # Drafts get a day's grace before they're flagged
    assert f"unpublished-{unfinished['id']}" not in ids(get(client, headers, base))
    with session_scope() as session:
        session.execute(
            update(Workflow).where(Workflow.id == unfinished["id"]).values(created_at=utc_now() - timedelta(days=2))
        )

    found = ids(get(client, headers, base))
    assert found[:2] == [f"failing-{failing['id']}", f"unpublished-{unfinished['id']}"]
    # WooCommerce shop: no Shopify cart template, and reviews are already installed
    assert "template-abandoned-cart" not in found and "template-reviews" not in found


def test_viewers_cannot_set_the_time_value(client, signup):
    headers, workspace_id = signup()
    base = f"/workspaces/{workspace_id}"
    viewer_headers, _ = signup(email="viewer@example.com")
    client.post(f"{base}/members", json={"email": "viewer@example.com", "role": "viewer"}, headers=headers)

    assert client.get(f"{base}/insights", headers=viewer_headers).status_code == 200
    assert client.put(f"{base}/insights/time-value", json={"per_hour": 10}, headers=viewer_headers).status_code == 403
