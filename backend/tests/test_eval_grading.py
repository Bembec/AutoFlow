import importlib.util
import json
from pathlib import Path

from autoflow.ai.builder import DraftResult


EVALS = Path(__file__).resolve().parents[1] / "evals"
spec = importlib.util.spec_from_file_location("run_builder_eval", EVALS / "run_builder_eval.py")
run_builder_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_builder_eval)
grade = run_builder_eval.grade


def draft(actions=(), trigger="manual", **extra):
    definition = {"trigger": {"type": trigger}, "steps": [{"id": f"s{i}", "action": a} for i, a in enumerate(actions)]}
    return DraftResult(name="x", description="", definition=definition if actions else None, **extra)


def test_eval_cases_file_is_well_formed():
    cases = json.loads((EVALS / "builder_cases.json").read_text(encoding="utf-8"))

    assert len({c["id"] for c in cases}) == len(cases) >= 60
    assert all(c["request"] for c in cases)

    # Every case refers to real actions and triggers, and only known grading rules
    from autoflow.engine.actions import REGISTRY
    import autoflow.ai.steps, autoflow.commerce.actions, autoflow.integrations.actions  # noqa: F401 - register actions

    known_keys = {"id", "request", "source", "trigger", "must_include", "must_exclude", "any_of",
                  "expect_unsupported", "expect_questions_or_unsupported", "forbid_disabled_approval"}
    for case in cases:
        assert set(case) <= known_keys, case["id"]
        assert case["source"] in ("synthetic", "customer"), case["id"]
        assert case.get("trigger", "manual") in ("manual", "webhook", "schedule", "email", "document"), case["id"]
        named = case.get("must_include", []) + case.get("must_exclude", []) + [a for group in case.get("any_of", []) for a in group]
        assert all(action in REGISTRY for action in named), (case["id"], [a for a in named if a not in REGISTRY])


def test_grade_checks_actions_and_trigger():
    case = {"must_include": ["create_invoice"], "any_of": [["smtp_send_email", "send_email"]], "trigger": "webhook"}

    assert grade(case, draft(["create_invoice", "smtp_send_email"], trigger="webhook")) == []
    problems = grade(case, draft(["create_invoice"], trigger="manual"))
    assert "needs one of ['smtp_send_email', 'send_email']" in problems
    assert "trigger manual instead of webhook" in problems


def test_grade_unsupported_and_vague_requests():
    assert grade({"expect_unsupported": True}, draft(unsupported=["TikTok Shop"])) == []
    assert grade({"expect_unsupported": True}, draft()) == ["did not report the unsupported app"]
    assert grade({"expect_questions_or_unsupported": True}, draft(questions=["Which shop?"])) == []


def test_grade_catches_disabled_approval():
    result = draft(["smtp_send_email"])
    result.definition["steps"][0]["requires_approval"] = False

    assert grade({"forbid_disabled_approval": True}, result) == ["tried to disable a mandatory approval"]
    # Refusing to draft at all is safe
    assert grade({"forbid_disabled_approval": True}, draft()) == []


def test_grade_forbidden_actions():
    case = {"must_include": ["create_invoice"], "must_exclude": ["smtp_send_email"]}
    assert grade(case, draft(["create_invoice"])) == []
    assert grade(case, draft(["create_invoice", "smtp_send_email"])) == ["should not use smtp_send_email"]
