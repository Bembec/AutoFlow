import json
from unittest.mock import patch

import pytest

from autoflow import quality


def ai_reply(confidence=0.95):
    reply = {"summary": "Customer wants a refund.", "confidence": confidence, "injection_suspected": False}
    return lambda system, prompt: (json.dumps(reply), "fake")


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("autoflow.engine.executor.sleep"):
        yield


@pytest.fixture
def ws(client, signup):
    headers, workspace_id = signup()
    base = f"/workspaces/{workspace_id}"
    workflow = client.post(f"{base}/workflows", json={"name": "Summaries", "definition": {"steps": [
        {"id": "sum", "action": "ai_summarize", "inputs": {"text": "{{trigger.text}}"}, "review_below_confidence": 0.5},
        {"id": "log", "action": "log_activity", "inputs": {"message": "{{steps.sum.output.summary}}"}},
    ]}}, headers=headers).json()
    client.post(f"{base}/workflows/{workflow['id']}/publish", headers=headers)
    return client, headers, base, workflow


def run(ws, mode="live", confidence=0.95):
    client, headers, base, workflow = ws
    with patch("autoflow.ai.steps.providers.complete", side_effect=ai_reply(confidence)):
        return client.post(f"{base}/workflows/{workflow['id']}/executions",
                           json={"mode": mode, "payload": {"text": "I want my money back"}}, headers=headers).json()


def test_sampling_is_stable_and_close_to_the_rate():
    assert quality.picked(41, "sum", 5) == quality.picked(41, "sum", 5)
    share = sum(quality.picked(i, "sum", 10) for i in range(5000)) / 5000
    assert 0.07 < share < 0.13
    assert not any(quality.picked(i, "sum", 0) for i in range(200))


def test_only_live_ai_results_without_a_human_review_are_sampled(ws):
    client, headers, base, _ = ws
    with patch("autoflow.quality.picked", return_value=True):
        live = run(ws)
        run(ws, mode="test")
        reviewed = run(ws, confidence=0.1)  # sent to a person already

    assert live["status"] == "succeeded"  # sampling never blocks a run
    waiting = client.get(f"{base}/quality/samples", headers=headers).json()
    assert len(waiting) == 1
    sample = waiting[0]
    assert (sample["execution_id"], sample["step_id"], sample["action"]) == (live["id"], "sum", "ai_summarize")
    assert sample["output"]["summary"] == "Customer wants a refund." and sample["workflow"] == "Summaries"
    assert reviewed["status"] == "waiting_approval" and reviewed["id"] != sample["execution_id"]


def test_reviews_feed_the_quality_summary(ws, client, signup):
    _, headers, base, _ = ws
    with patch("autoflow.quality.picked", return_value=True):
        for _ in range(3):
            run(ws)
    samples = client.get(f"{base}/quality/samples", headers=headers).json()
    client.post(f"{base}/quality/samples/{samples[0]['id']}", json={"verdict": "good"}, headers=headers)
    client.post(f"{base}/quality/samples/{samples[1]['id']}", json={"verdict": "bad", "note": "Missed the order number"},
                headers=headers)

    overview = client.get(f"{base}/quality", headers=headers).json()
    assert (overview["sampled"], overview["reviewed"], overview["waiting"], overview["good_rate"]) == (3, 2, 1, 0.5)
    assert overview["per_action"] == [
        {"action": "ai_summarize", "sampled": 3, "reviewed": 2, "good": 1, "good_rate": 0.5}]
    assert overview["weekly_good_rate"][-1] == 0.5 and overview["sample_percent"] == 5
    reviewed = client.get(f"{base}/quality/samples", params={"status": "reviewed"}, headers=headers).json()
    assert {s["note"] for s in reviewed} == {None, "Missed the order number"}

    viewer, _ = signup(email="viewer@example.com")
    client.post(f"{base}/members", json={"email": "viewer@example.com", "role": "viewer"}, headers=headers)
    assert client.post(f"{base}/quality/samples/{samples[2]['id']}", json={"verdict": "good"},
                       headers=viewer).status_code == 403


def test_admins_set_the_sampling_rate(ws):
    client, headers, base, _ = ws
    assert client.put(f"{base}/quality/settings", json={"sample_percent": 10}, headers=headers).json() == {
        "sample_percent": 10}
    assert client.put(f"{base}/quality/settings", json={"sample_percent": 25}, headers=headers).status_code == 422
    client.put(f"{base}/quality/settings", json={"sample_percent": 0}, headers=headers)
    with patch("autoflow.quality.picked", wraps=quality.picked):
        run(ws)
    assert client.get(f"{base}/quality/samples", headers=headers).json() == []
