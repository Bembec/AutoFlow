"""
Values that refer to earlier data, written as {{ path }}.

Paths start at `trigger` (the data that started the run) or
`steps.<step_id>.output` (what an earlier step returned), e.g.

    "{{trigger.email}}"
    "Hello {{trigger.name}}"
    "{{steps.classify.output.category}}"

A value that is exactly one reference keeps the referenced type; a
reference inside longer text is converted to text. Missing values become
None (or "" inside text).
"""

import re


REFERENCE = re.compile(r"\{\{\s*([A-Za-z0-9_.\-]+)\s*\}\}")


def find_references(value):
    """Yield every reference path used anywhere inside a value."""

    if isinstance(value, str):
        yield from REFERENCE.findall(value)
    elif isinstance(value, dict):
        for item in value.values():
            yield from find_references(item)
    elif isinstance(value, list):
        for item in value:
            yield from find_references(item)


def resolve_path(path, context):
    current = context

    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None

    return current


def render(value, context):
    """Replace every reference inside a value using the context."""

    if isinstance(value, str):
        whole = REFERENCE.fullmatch(value.strip())

        if whole:
            return resolve_path(whole.group(1), context)

        def substitute(match):
            resolved = resolve_path(match.group(1), context)
            return "" if resolved is None else str(resolved)

        return REFERENCE.sub(substitute, value)

    if isinstance(value, dict):
        return {key: render(item, context) for key, item in value.items()}

    if isinstance(value, list):
        return [render(item, context) for item in value]

    return value


def _number(value):
    """A number from 47.6, "47.60" or "1,200.50"; None if it isn't one."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def evaluate_condition(condition, context):
    """Return True when a step's `when` condition (or AND/OR group) holds."""

    if getattr(condition, "all", None) is not None:
        return all(evaluate_condition(part, context) for part in condition.all)
    if getattr(condition, "any", None) is not None:
        return any(evaluate_condition(part, context) for part in condition.any)

    left = render(condition.left, context)
    right = render(condition.right, context)

    match condition.op:
        case "eq":
            return left == right
        case "neq":
            return left != right
        case "contains":
            return right is not None and str(right).lower() in str(left or "").lower()
        case "exists":
            # An empty list or object has no value either (e.g. no proposals)
            return left not in (None, "") and left != [] and left != {}
        case "not_exists":
            return left in (None, "") or left == [] or left == {}
        case "not_contains":
            return right is None or str(right).lower() not in str(left or "").lower()
        case "gt" | "gte" | "lt" | "lte":
            a, b = _number(left), _number(right)
            # Not numbers: the comparison is simply false, never an error
            if a is None or b is None:
                return False
            return {"gt": a > b, "gte": a >= b, "lt": a < b, "lte": a <= b}[condition.op]

    raise ValueError(f"Unknown operator: {condition.op}")
