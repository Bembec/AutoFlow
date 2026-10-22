from datetime import timedelta

from sqlalchemy import update

from autoflow.accounts.security import hash_password, verify_password
from autoflow.storage.db import engine, utc_now
from autoflow.storage.models import AccessToken


def test_password_hashing():
    stored = hash_password("correct-horse")

    assert stored != "correct-horse"
    assert verify_password("correct-horse", stored)
    assert not verify_password("wrong-horse", stored)


def test_register_creates_owned_workspace(client, signup):
    headers, _ = signup(name="Ada")

    me = client.get("/me", headers=headers).json()

    assert me["email"] == "owner@example.com"
    assert me["workspaces"][0]["role"] == "owner"
    assert me["workspaces"][0]["name"] == "Ada's workspace"


def test_duplicate_registration_is_rejected(client, signup):
    signup()

    response = client.post(
        "/auth/register",
        json={"email": "OWNER@example.com", "name": "Again", "password": "something-long"},
    )

    assert response.status_code == 409


def test_wrong_password_and_missing_token(client, signup):
    signup()

    assert client.post(
        "/auth/login", json={"email": "owner@example.com", "password": "nope-nope"}
    ).status_code == 401
    assert client.get("/me").status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_logout_revokes_token(client, signup):
    headers, _ = signup()

    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/me", headers=headers).status_code == 401


def test_expired_token_is_rejected(client, signup):
    headers, _ = signup()

    with engine.begin() as connection:
        connection.execute(
            update(AccessToken).values(expires_at=utc_now() - timedelta(minutes=1))
        )

    assert client.get("/me", headers=headers).status_code == 401


def test_workspaces_are_isolated(client, signup):
    owner_headers, owner_workspace = signup("owner@example.com")
    other_headers, other_workspace = signup("other@example.com")

    client.post(f"/workspaces/{owner_workspace}/workflow-runs", headers=owner_headers)

    # The other business cannot see the workspace at all
    for path in ("customers", "workflow-runs", "approvals", "members"):
        response = client.get(
            f"/workspaces/{owner_workspace}/{path}", headers=other_headers
        )
        assert response.status_code == 404

    # And their own workspace is empty
    assert client.get(
        f"/workspaces/{other_workspace}/customers", headers=other_headers
    ).json() == []


def test_same_customer_email_in_two_workspaces(client, signup):
    first_headers, first_workspace = signup("first@example.com")
    second_headers, second_workspace = signup("second@example.com")

    client.post(f"/workspaces/{first_workspace}/workflow-runs", headers=first_headers)
    client.post(f"/workspaces/{second_workspace}/workflow-runs", headers=second_headers)

    for headers, workspace_id in (
        (first_headers, first_workspace),
        (second_headers, second_workspace),
    ):
        customers = client.get(
            f"/workspaces/{workspace_id}/customers", headers=headers
        ).json()
        assert len(customers) == 4


def test_roles_limit_actions(client, signup):
    owner_headers, workspace_id = signup("owner@example.com")
    viewer_headers, _ = signup("viewer@example.com")
    base = f"/workspaces/{workspace_id}"

    response = client.post(
        f"{base}/members",
        json={"email": "viewer@example.com", "role": "viewer"},
        headers=owner_headers,
    )
    assert response.status_code == 201

    # A viewer can read but not run workflows or add members
    assert client.get(f"{base}/customers", headers=viewer_headers).status_code == 200
    assert client.post(f"{base}/workflow-runs", headers=viewer_headers).status_code == 403
    assert client.post(
        f"{base}/members",
        json={"email": "owner@example.com", "role": "owner"},
        headers=viewer_headers,
    ).status_code == 403

    members = client.get(f"{base}/members", headers=owner_headers).json()
    assert {m["role"] for m in members} == {"owner", "viewer"}


def test_admin_cannot_grant_owner(client, signup):
    owner_headers, workspace_id = signup("owner@example.com")
    admin_headers, _ = signup("admin@example.com")
    signup("someone@example.com")
    base = f"/workspaces/{workspace_id}"

    client.post(
        f"{base}/members",
        json={"email": "admin@example.com", "role": "admin"},
        headers=owner_headers,
    )

    response = client.post(
        f"{base}/members",
        json={"email": "someone@example.com", "role": "owner"},
        headers=admin_headers,
    )

    assert response.status_code == 409


def test_create_extra_workspace(client, signup):
    headers, _ = signup()

    response = client.post("/workspaces", json={"name": "Second Shop"}, headers=headers)

    assert response.status_code == 201
    assert response.json()["slug"] == "second-shop"
    assert len(client.get("/me", headers=headers).json()["workspaces"]) == 2
