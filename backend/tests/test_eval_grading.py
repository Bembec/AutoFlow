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

    assert len({c["id"] for c in cases}) == len(cases) >= 15
    assert all(c["request"] for c in cases)


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
