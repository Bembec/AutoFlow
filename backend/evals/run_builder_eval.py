"""
AI workflow builder quality check (the roadmap's "AI quality test set").

Runs plain-language requests through the AI builder and checks each draft:
it must validate, use the expected actions and trigger, admit unsupported
apps instead of inventing them, ask questions when the request is vague,
and never switch off a mandatory approval.

    python evals/run_builder_eval.py               # all cases (calls the AI!)
    python evals/run_builder_eval.py --limit 3     # first 3 cases
    python evals/run_builder_eval.py --case cart-reminder

Release gate: before any model or prompt change ships, the share of
cases drafted correctly on the FIRST attempt must be at least
--min-first-time (default 0.80, the MVP gate). The command exits non-zero
otherwise. Results are saved to data/output/evals/.

The cases are synthetic until design partners supply real requests
("source" field); replace and extend them with real ones (target 200+).
Each case costs one to three AI calls; use fake data only.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from luphina import config
from luphina.ai import builder, providers


CASES_FILE = Path(__file__).with_name("builder_cases.json")


def grade(case, draft):
    """Return a list of problems (empty list = pass)."""

    problems = []
    definition = draft.definition
    actions = [step["action"] for step in definition["steps"]] if definition else []

    if case.get("expect_unsupported"):
        if not draft.unsupported:
            problems.append("did not report the unsupported app")
        return problems

    if case.get("expect_questions_or_unsupported"):
        if not (draft.questions or draft.unsupported):
            problems.append("did not ask for details on a vague request")
        return problems

    if case.get("forbid_disabled_approval"):
        # Refusing to draft is a safe outcome; only an unsafe draft fails
        for step in (definition or {}).get("steps", []):
            if step["action"] in ("send_email", "smtp_send_email") and step.get("requires_approval") is False:
                problems.append("tried to disable a mandatory approval")
        return problems

    if definition is None:
        return [f"no workflow drafted (questions: {draft.questions})"]

    for action in case.get("must_include", []):
        if action not in actions:
            problems.append(f"missing action {action}")

    for action in case.get("must_exclude", []):
        if action in actions:
            problems.append(f"should not use {action}")

    for options in case.get("any_of", []):
        if not any(option in actions for option in options):
            problems.append(f"needs one of {options}")

    if case.get("trigger") and definition["trigger"]["type"] != case["trigger"]:
        problems.append(f"trigger {definition['trigger']['type']} instead of {case['trigger']}")

    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--case")
    parser.add_argument("--min-first-time", type=float, default=0.80,
                        help="share of cases that must pass on the first AI attempt (release gate)")
    args = parser.parse_args()

    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
    if args.limit:
        cases = cases[: args.limit]

    results = []
    for case in cases:
        started = time.perf_counter()
        try:
            draft = builder.draft_workflow(case["request"])
            problems = grade(case, draft)
            detail = {
                "provider": draft.provider,
                "attempts": draft.attempts,
                "actions": [s["action"] for s in draft.definition["steps"]] if draft.definition else [],
            }
        except (builder.DraftFailed, providers.AIUnavailable) as error:
            problems, detail = [f"error: {error}"], {}

        passed = not problems
        results.append({"id": case["id"], "passed": passed, "problems": problems,
                        "seconds": round(time.perf_counter() - started, 1), **detail})
        print(f"{'PASS' if passed else 'FAIL'}  {case['id']:<22} {'; '.join(problems)}")

    score = sum(r["passed"] for r in results)
    # "Correct first time": passed without the builder having to retry
    first_time = sum(r["passed"] and r.get("attempts", 1) <= 1 for r in results)
    rate = first_time / len(results) if results else 0.0
    print(f"\n{score}/{len(results)} passed; {first_time} first time ({rate:.0%}, gate {args.min_first_time:.0%})")

    out_dir = config.OUTPUT_DIR / "evals"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (out_dir / f"builder-{stamp}.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    return 0 if rate >= args.min_first_time else 1


if __name__ == "__main__":
    sys.exit(main())
