"""
Production evaluations: a random share of live AI results is kept for a
person to judge, so AI quality is measured on real work, not only on the
test set before a release.

Sampling never blocks or slows a run. It is deterministic per (run, step),
so the same step is never sampled twice and tests can predict it.
Results already sent to a human review (low confidence, suspected prompt
injection) are not sampled again: a person already looked at them.
"""

import hashlib
import json
from collections import defaultdict
from datetime import timedelta

from sqlalchemy import select

from autoflow.storage.db import utc_now
from autoflow.storage.models import QualitySample

MAX_PERCENT = 20
MAX_STORED_CHARS = 4000
WEEKS = 8


def is_ai_step(action_name):
    from autoflow.ai.steps import AI_ACTIONS

    return action_name in AI_ACTIONS or action_name == "ai_agent"


def picked(execution_id, step_id, percent):
    """True for about `percent`% of (run, step) pairs, always the same answer for the same pair."""
    if percent <= 0:
        return False
    digest = hashlib.sha256(f"{execution_id}:{step_id}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % 100 < percent


def _trim(value):
    """Keep stored samples small: long values are cut, not dropped."""
    text = json.dumps(value, ensure_ascii=False, default=str)
    if len(text) <= MAX_STORED_CHARS:
        return value
    return {"truncated": True, "preview": text[:MAX_STORED_CHARS]}


def maybe_sample(session, workspace, execution, step_id, action_name, inputs, output):
    """Keep this live AI result for review if it is picked. Not committed here."""
    if execution.mode != "live" or not is_ai_step(action_name):
        return None
    if not picked(execution.id, step_id, min(MAX_PERCENT, workspace.quality_sample_percent or 0)):
        return None
    sample = QualitySample(
        workspace_id=workspace.id, execution_id=execution.id, workflow_id=execution.workflow_id,
        step_id=step_id, action=action_name, input=_trim(inputs), output=_trim(output),
        confidence=output.get("confidence") if isinstance(output.get("confidence"), (int, float)) else None,
    )
    session.add(sample)
    return sample


def summary(session, workspace_id, days=30):
    since = utc_now() - timedelta(days=days)
    samples = session.scalars(select(QualitySample).where(
        QualitySample.workspace_id == workspace_id, QualitySample.created_at >= utc_now() - timedelta(weeks=WEEKS),
    )).all()

    recent = [s for s in samples if s.created_at >= since]
    reviewed = [s for s in recent if s.verdict]
    per_action = defaultdict(lambda: {"sampled": 0, "reviewed": 0, "good": 0})
    for sample in recent:
        row = per_action[sample.action]
        row["sampled"] += 1
        row["reviewed"] += bool(sample.verdict)
        row["good"] += sample.verdict == "good"

    now = utc_now()
    weekly = [{"reviewed": 0, "good": 0} for _ in range(WEEKS)]
    for sample in samples:
        if not sample.verdict:
            continue
        age = max(0, min(WEEKS - 1, int((now - sample.created_at).total_seconds() // (7 * 24 * 3600))))
        weekly[WEEKS - 1 - age]["reviewed"] += 1
        weekly[WEEKS - 1 - age]["good"] += sample.verdict == "good"

    def rate(good, total):
        return round(good / total, 3) if total else None

    return {
        "sampled": len(recent),
        "waiting": len(recent) - len(reviewed),
        "reviewed": len(reviewed),
        "good_rate": rate(sum(s.verdict == "good" for s in reviewed), len(reviewed)),
        "per_action": [
            {"action": action, **row, "good_rate": rate(row["good"], row["reviewed"])}
            for action, row in sorted(per_action.items())
        ],
        "weekly_good_rate": [rate(week["good"], week["reviewed"]) for week in weekly],
    }
