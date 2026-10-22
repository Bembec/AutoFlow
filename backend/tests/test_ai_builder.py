import json
from unittest.mock import patch

import pytest

from autoflow.ai import providers
from autoflow.ai.builder import extract_json


VALID_DRAFT = {
    "name": "Support auto-reply",
    "description": "Reply to support enquiries.",
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": {"name": "Ada", "email": "a@b.co", "message": "help"}},
        "steps": [
            {"id": "classify", "action": "classify_enquiry", "inputs": {"message": "{{trigger.message}}"}},
            {
                "id": "compose",
                "action": "compose_email",
                "inputs": {
                    "name": "{{trigger.name}}",
                    "email": "{{trigger.email}}",
                    "category": "{{steps.classify.output.category}}",
                },
            },
            {
                "id": "send",
                "action": "send_email",
                "inputs": {
                    "to": "{{steps.compose.output.to}}",
                    "subject": "{{steps.compose.output.subject}}",
                    "body": "{{steps.compose.output.body}}",
                },
            },
        ],
    },
    "questions": [],
    "assumptions": ["Replies go to the enquiry's email."],
    "unsupported": [],
}

INVALID_DRAFT = {
    **VALID_DRAFT,
    "definition": {"steps": [{"id": "x", "action": "post_to_slack", "inputs": {}}]},
}


def replies(*texts):
    """Patch the router so the AI returns these replies in order."""

    answers = iter(texts)
    return patch(
        "autoflow.ai.builder.providers.complete",
        side_effect=lambda system, prompt: (next(answers), "fake"),
    )


@pytest.fixture
def ws(client, signup):
    headers, workspace_id = signup()
    return client, headers, f"/workspaces/{workspace_id}"


def draft(ws, **body):
    client, headers, base = ws
    body.setdefault("request", "Reply to every support email automatically")
    return client.post(f"{base}/workflows/ai-draft", json=body, headers=headers)


def test_valid_draft_is_returned(ws):
    with replies("```json\n" + json.dumps(VALID_DRAFT) + "\n```"):
        response = draft(ws)

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ready"
    assert body["attempts"] == 1
    assert [s["id"] for s in body["definition"]["steps"]] == ["classify", "compose", "send"]
    assert body["workflow"] is None


def test_invalid_draft_is_repaired(ws):
    with replies(json.dumps(INVALID_DRAFT), json.dumps(VALID_DRAFT)) as fake:
        body = draft(ws).json()

    assert body["status"] == "ready"
    assert body["attempts"] == 2
    # The validator's complaint was sent back to the AI
    assert "unknown action post_to_slack" in fake.call_args_list[1].args[1]


def test_never_valid_draft_fails_cleanly(ws):
    with replies(*[json.dumps(INVALID_DRAFT)] * 3):
        response = draft(ws)

    assert response.status_code == 422
    assert "could not produce a valid workflow" in response.json()["detail"]


def test_disabling_mandatory_approval_is_never_accepted(ws):
    sneaky = json.loads(json.dumps(VALID_DRAFT))
    sneaky["definition"]["steps"][2]["requires_approval"] = False

    with replies(*[json.dumps(sneaky)] * 3):
        assert draft(ws).status_code == 422


def test_questions_when_details_are_missing(ws):
    reply = {
        "name": "Invoices", "description": "", "definition": None,
        "questions": ["Which accounting app do you use?"],
        "assumptions": [], "unsupported": ["QuickBooks"],
    }

    with replies(json.dumps(reply)):
        body = draft(ws, request="Create invoices for every new order").json()

    assert body["status"] == "needs_details"
    assert body["questions"] == ["Which accounting app do you use?"]
    assert body["unsupported"] == ["QuickBooks"]


def test_answers_are_sent_to_the_ai(ws):
    with replies(json.dumps(VALID_DRAFT)) as fake:
        draft(ws, answers=[{"question": "Which inbox?", "answer": "support@shop.example"}])

    assert "support@shop.example" in fake.call_args.args[1]


def test_save_creates_a_draft_workflow(ws):
    client, headers, base = ws

    with replies(json.dumps(VALID_DRAFT)):
        body = draft(ws, save=True).json()

    workflow = body["workflow"]
    assert workflow["name"] == "Support auto-reply"
    assert workflow["versions"][0]["state"] == "draft"
    assert len(client.get(f"{base}/workflows", headers=headers).json()) == 1


def test_no_provider_configured_returns_503(ws):
    response = draft(ws)

    assert response.status_code == 503
    assert "No AI provider" in response.json()["detail"]


def test_viewers_cannot_draft(client, signup):
    owner_headers, workspace_id = signup("owner@example.com")
    viewer_headers, _ = signup("viewer@example.com")
    base = f"/workspaces/{workspace_id}"
    client.post(
        f"{base}/members", json={"email": "viewer@example.com", "role": "viewer"}, headers=owner_headers
    )

    response = client.post(
        f"{base}/workflows/ai-draft",
        json={"request": "Reply to every support email"},
        headers=viewer_headers,
    )

    assert response.status_code == 403


# --- router -----------------------------------------------------------------

def test_router_falls_back_to_next_provider(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "y")

    with (
        patch.object(providers.GeminiProvider, "complete", side_effect=RuntimeError("outage")),
        patch.object(providers.AnthropicProvider, "complete", return_value="{}"),
    ):
        assert providers.complete("s", "p") == ("{}", "anthropic")


def test_router_respects_order_and_reports_all_failures(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "y")
    monkeypatch.setenv("AI_PROVIDER_ORDER", "anthropic,gemini")

    with (
        patch.object(providers.GeminiProvider, "complete", side_effect=RuntimeError("g down")),
        patch.object(providers.AnthropicProvider, "complete", side_effect=RuntimeError("a down")),
        pytest.raises(providers.AIUnavailable) as error,
    ):
        providers.complete("s", "p")

    assert str(error.value).index("anthropic") < str(error.value).index("gemini")


def test_extract_json_handles_surrounding_text():
    assert extract_json('Here you go:\n{"a": 1}\nThanks') == {"a": 1}

    with pytest.raises(ValueError):
        extract_json("no json here")
