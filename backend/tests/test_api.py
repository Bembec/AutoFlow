def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_run_workflow_then_read_results(client, signup, no_external_calls):
    headers, workspace_id = signup()
    base = f"/workspaces/{workspace_id}"

    response = client.post(f"{base}/workflow-runs", headers=headers)

    assert response.status_code == 201
    result = response.json()
    assert result["customer_count"] == 4
    assert result["categories"] == {"Sales": 2, "Support": 1, "Other": 1}
    assert result["emails"] == []

    # The .env Airtable account belongs to the local operator only
    no_external_calls.assert_not_called()

    runs = client.get(f"{base}/workflow-runs", params={"limit": 1}, headers=headers).json()
    assert runs[0]["id"] == result["run_id"]

    sales = client.get(
        f"{base}/customers", params={"category": "Sales"}, headers=headers
    ).json()
    assert {customer["email"] for customer in sales} == {
        "ada@example.com",
        "david@example.com",
    }

    detail = client.get(f"{base}/customers/{sales[0]['id']}", headers=headers).json()
    assert detail["quote_usd"] == "110.00"


def test_unknown_customer_returns_404(client, signup):
    headers, workspace_id = signup()

    response = client.get(f"/workspaces/{workspace_id}/customers/999999", headers=headers)

    assert response.status_code == 404


def test_invalid_category_is_rejected(client, signup):
    headers, workspace_id = signup()

    response = client.get(
        f"/workspaces/{workspace_id}/customers",
        params={"category": "Spam"},
        headers=headers,
    )

    assert response.status_code == 422


def test_dashboard_reports_time_saved(client, signup):
    headers, workspace_id = signup()
    base = f"/workspaces/{workspace_id}"
    definition = {"steps": [{"id": "log", "action": "log_activity", "inputs": {"message": "x"}}]}
    workflow = client.post(
        f"{base}/workflows",
        json={"name": "Log", "definition": definition, "minutes_saved_per_run": 12},
        headers=headers,
    ).json()
    client.post(f"{base}/workflows/{workflow['id']}/publish", headers=headers)

    for mode in ("live", "live", "test"):
        client.post(f"{base}/workflows/{workflow['id']}/executions", json={"mode": mode}, headers=headers)

    dashboard = client.get(f"{base}/dashboard", headers=headers).json()

    # Test runs do not count as time saved
    assert dashboard["minutes_saved_30d"] == 24
    assert dashboard["per_workflow"][0]["runs_succeeded_30d"] == 2
    assert dashboard["executions_today"] == {"succeeded": 3}
    assert dashboard["recent_executions"][0]["workflow_name"] == "Log"
