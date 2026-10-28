from unittest.mock import patch

import pytest

from autoflow.accounts import two_factor


# --- TOTP algorithm -------------------------------------------------------------------

def test_totp_matches_rfc_6238_test_vector():
    # RFC 6238 appendix B: secret "12345678901234567890", T = 59 s -> 94287082 (8 digits)
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
    with patch.object(two_factor, "DIGITS", 8):
        assert two_factor.code_at(secret, 59 // 30) == "94287082"


def test_codes_accept_small_clock_drift_but_not_reuse():
    secret = two_factor.new_secret()
    now = 1_800_000_000
    step = two_factor.current_step(now)

    assert two_factor.matching_step(secret, two_factor.code_at(secret, step), now=now) == step
    assert two_factor.matching_step(secret, two_factor.code_at(secret, step - 1), now=now) == step - 1
    assert two_factor.matching_step(secret, two_factor.code_at(secret, step - 3), now=now) is None
    # Already used up to this step: the same code is refused
    assert two_factor.matching_step(secret, two_factor.code_at(secret, step), last_step=step, now=now) is None
    assert two_factor.matching_step(secret, "12345", now=now) is None


# --- two-factor login flow ---------------------------------------------------------------

def login(client, code=None, password="correct-horse"):
    body = {"email": "owner@example.com", "password": password}
    if code:
        body["code"] = code
    return client.post("/auth/login", json=body)


def enable_2fa(client, headers):
    setup = client.post("/auth/2fa/setup", headers=headers).json()
    assert setup["otpauth_uri"].startswith("otpauth://totp/Luphina:")
    secret = setup["secret"]
    code = two_factor.code_at(secret, two_factor.current_step())
    enabled = client.post("/auth/2fa/enable", json={"code": code}, headers=headers).json()
    return secret, enabled["recovery_codes"]


def test_two_factor_login(client, signup):
    headers, _ = signup()
    secret, recovery = enable_2fa(client, headers)
    assert len(recovery) == 10

    # Password alone is no longer enough
    response = login(client)
    assert response.status_code == 401
    assert response.json()["detail"] == "two_factor_required"

    assert login(client, code="000000").status_code == 401

    # The code used to enable is already spent; the next step's code works
    next_code = two_factor.code_at(secret, two_factor.current_step() + 1)
    assert login(client, code=next_code).status_code == 200
    assert login(client, code=next_code).status_code == 401  # never twice


def test_recovery_codes_work_once(client, signup):
    headers, _ = signup()
    _, recovery = enable_2fa(client, headers)

    assert login(client, code=recovery[0]).status_code == 200
    assert login(client, code=recovery[0]).status_code == 401
    assert client.get("/auth/2fa", headers=headers).json() == {"enabled": True, "recovery_codes_left": 9}


def test_disabling_needs_password_and_code(client, signup):
    headers, _ = signup()
    secret, recovery = enable_2fa(client, headers)

    wrong = client.post("/auth/2fa/disable", json={"password": "nope-nope", "code": recovery[0]}, headers=headers)
    assert wrong.status_code == 409

    ok = client.post("/auth/2fa/disable", json={"password": "correct-horse", "code": recovery[1]}, headers=headers)
    assert ok.json() == {"enabled": False}
    assert login(client).status_code == 200


def test_cannot_enable_with_a_wrong_code(client, signup):
    headers, _ = signup()
    client.post("/auth/2fa/setup", headers=headers)

    response = client.post("/auth/2fa/enable", json={"code": "123456"}, headers=headers)

    assert response.status_code == 409
    assert client.get("/auth/2fa", headers=headers).json()["enabled"] is False


# --- audit log ---------------------------------------------------------------------------------

@pytest.fixture
def team(client, signup):
    owner_headers, workspace_id = signup("owner@example.com")
    member_headers, _ = signup("member@example.com")
    base = f"/workspaces/{workspace_id}"
    client.post(f"{base}/members", json={"email": "member@example.com", "role": "member"}, headers=owner_headers)
    return client, owner_headers, member_headers, base


def test_actions_are_audited(team):
    client, owner, _, base = team
    client.post(f"{base}/connections", json={
        "provider": "airtable", "name": "crm", "config": {"base_id": "app1"}, "secrets": {"token": "pat-secret-123456"},
    }, headers=owner)
    workflow = client.post(f"{base}/workflows", json={"name": "Flow", "definition": {
        "steps": [{"id": "log", "action": "log_activity", "inputs": {"message": "x"}}]}}, headers=owner).json()
    client.post(f"{base}/workflows/{workflow['id']}/publish", headers=owner)
    client.post(f"{base}/emergency-stop", json={"reason": "test"}, headers=owner)
    client.get(f"{base}/export", headers=owner)

    events = client.get(f"{base}/audit", headers=owner).json()
    actions = [e["action"] for e in events]

    for expected in ("member.added", "connection.created", "workflow.published", "automation.emergency_stop", "data.exported"):
        assert expected in actions
    assert events[0]["action"] == "data.exported"  # newest first
    assert all(e["user"] == "owner@example.com" for e in events)
    assert "pat-secret" not in str(events)


def test_audit_log_is_admin_only(team):
    client, _, member, base = team

    assert client.get(f"{base}/audit", headers=member).status_code == 403


def test_sign_ins_are_recorded_with_ip(client, signup):
    headers, _ = signup()
    login(client, password="wrong-password")

    activity = client.get("/auth/activity", headers=headers).json()

    actions = [a["action"] for a in activity]
    assert actions[:2] == ["auth.login_failed", "auth.login"]
    assert activity[0]["ip"]
