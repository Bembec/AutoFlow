"""
Compare two versions of a workflow: what publishing (or rolling back) changes.

Steps are matched by id, so a renamed or edited step shows as "changed"
rather than removed and added. The result is a list of plain changes the
app turns into sentences, e.g.

    {"kind": "changed", "step_id": "send", "name": "Email the invoice",
     "fields": [{"field": "when", "before": None, "after": {...}}]}
"""

STEP_FIELDS = (
    "name", "action", "inputs", "when", "for_each", "retry", "timeout_seconds",
    "requires_approval", "review_below_confidence",
)
TRIGGER_FIELDS = ("type", "schedule", "connection", "folder")


def _changed_fields(before, after, fields):
    changes = []
    for field in fields:
        old, new = before.get(field), after.get(field)
        if field == "inputs":
            old, new = old or {}, new or {}
            # One entry per input, so a long template shows what actually moved
            for key in sorted(set(old) | set(new)):
                if old.get(key) != new.get(key):
                    changes.append({"field": f"inputs.{key}", "before": old.get(key), "after": new.get(key)})
            continue
        if old != new:
            changes.append({"field": field, "before": old, "after": new})
    return changes


def compare(before, after):
    """Changes from definition `before` to `after` (both plain dicts)."""

    changes = []
    trigger = _changed_fields(before.get("trigger") or {}, after.get("trigger") or {}, TRIGGER_FIELDS)
    if trigger:
        changes.append({"kind": "trigger", "fields": trigger})

    old_steps = {step["id"]: (index, step) for index, step in enumerate(before.get("steps", []))}
    new_steps = {step["id"]: (index, step) for index, step in enumerate(after.get("steps", []))}

    for step_id, (_, step) in old_steps.items():
        if step_id not in new_steps:
            changes.append({"kind": "removed", "step_id": step_id, "name": step.get("name") or step_id,
                            "action": step.get("action")})

    # Order among the steps both versions share (added/removed steps don't count as moves)
    shared_old = [s for s in old_steps if s in new_steps]
    shared_new = [s for s in new_steps if s in old_steps]

    for step_id, (index, step) in new_steps.items():
        if step_id not in old_steps:
            changes.append({"kind": "added", "step_id": step_id, "name": step.get("name") or step_id,
                            "action": step.get("action"), "position": index + 1})
            continue
        fields = _changed_fields(old_steps[step_id][1], step, STEP_FIELDS)
        moved = shared_old.index(step_id) != shared_new.index(step_id)
        if fields or moved:
            changes.append({"kind": "changed", "step_id": step_id, "name": step.get("name") or step_id,
                            "action": step.get("action"), "fields": fields, "moved": moved,
                            "position": index + 1})
    return changes
