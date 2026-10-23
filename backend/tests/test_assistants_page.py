import json
from unittest.mock import patch

import pytest
from sqlalchemy import update

from autoflow.engine.templates_assistants import SAMPLE_SUPPORT_EMAIL
from autoflow.storage.db import session_scope
from autoflow.storage.models import Workspace

ROLES = ["assistant-support-inbox", "assistant-order-watcher", "assistant-refund-helper"]


def final(answer="Thanks for writing! Your order is being packed.", proposals=()):
    reply = {"final": {"answer": answer, "confidence": 0.9, "proposals": list(proposals)}}
    return lambda system, prompt: (json.dumps(reply), "fake")


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("autoflow.engine.executor.sleep"):
        yield


@pytest.fixture
def ws(client, signup):
    headers, workspace_id = signup()
    with session_scope() as session:
        session.execute(update(Workspace).where(Workspace.id == workspace_id)
                        .values(feature_flags={"ai_assistants": True}))
    return client, headers, f"/workspaces/{workspace_id}"


def install(ws, slug, publish=True):
    client, headers, base = ws
    workflow = client.post(f"{base}/workflows/from-template", json={"template": slug}, headers=headers).json()
    if publish:
        client.post(f"{base}/workflows/{workflow['id']}/publish", headers=headers)
    return workflow


def run(ws, workflow, mode="test", payload=None):
    client, headers, base = ws
    body = {"mode": mode, **({"payload": payload} if payload is not None else {})}
    return client.post(f"{base}/workflows/{workflow['id']}/executions", json=body, headers=headers).json()


def test_roles_are_listed_with_what_they_can_do(ws):
    client, headers, base = ws
    page = client.get(f"{base}/assistants", headers=headers).json()
    roles = {role["slug"]: role for role in page["roles"]}
    assert set(roles) == set(ROLES) and page["active"] == []
    assert roles["assistant-support-inbox"]["looks_up"] == ["checkout_status"]
    assert roles["assistant-refund-helper"]["proposes"] == ["void_invoice", "shopify_set_order_note"]


def test_the_page_needs_the_feature(client, signup):
    headers, workspace_id = signup(email="plain@example.com")
    assert client.get(f"/workspaces/{workspace_id}/assistants", headers=headers).status_code == 403


@pytest.mark.parametrize("slug", ROLES)
def test_every_role_test_runs(ws, slug):
    proposal = {"tool": "shopify_tag_order", "inputs": {"order_id": 1, "tags": "vip"}, "why": "big order"}
    if slug == "assistant-refund-helper":
        proposal = {"tool": "void_invoice", "inputs": {"order_ref": "820982911946154508"}, "why": "broken mug"}
    with patch("autoflow.ai.agent.providers.complete", side_effect=final(proposals=[proposal])):
        done = run(ws, install(ws, slug, publish=False))
    assert done["status"] == "succeeded", done["error"]
    steps = {s["step_id"]: s for s in done["steps"]}
    assert steps["act"]["output"]["dry_run"] is True


def test_no_proposals_means_nothing_to_approve(ws):
    with patch("autoflow.ai.agent.providers.complete", side_effect=final("An ordinary order.")):
        done = run(ws, install(ws, "assistant-order-watcher"), mode="live")
    assert done["status"] == "succeeded"
    assert {s["step_id"]: s["status"] for s in done["steps"]}["act"] == "skipped"


def test_active_assistants_report_their_week(ws):
    client, headers, base = ws
    support = install(ws, "assistant-support-inbox")
    proposal = {"tool": "shopify_tag_order", "inputs": {"order_id": 1001, "tags": "needs-human"}, "why": "late order"}
    with patch("autoflow.ai.agent.providers.complete", side_effect=final(proposals=[proposal])):
        waiting = run(ws, support, mode="live", payload=SAMPLE_SUPPORT_EMAIL)
    assert waiting["status"] == "waiting_approval"

    active = client.get(f"{base}/assistants", headers=headers).json()["active"]
    assert active == [{
        "workflow_id": support["id"], "name": "Support inbox assistant", "role": "assistant-support-inbox",
        "status": "active", "live": True, "handled_7d": 1, "succeeded_7d": 0, "failed_7d": 0, "waiting_approval": 1,
    }]
