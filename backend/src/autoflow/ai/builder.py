"""
AI workflow builder: plain-language request -> validated workflow draft.

The AI only drafts. Every draft passes the same validator as hand-written
workflows (unknown actions, bad references and disabled mandatory
approvals are rejected). If validation fails, the errors are sent back to
the AI for up to MAX_REPAIRS corrections. A person still tests and
publishes the result.
"""

import json
from dataclasses import dataclass, field

from pydantic import ValidationError

from autoflow.ai import providers
from autoflow.ai.providers import extract_json
from autoflow.engine.actions import describe_actions
from autoflow.engine.definition import WorkflowDefinition
from autoflow.engine.templates import ENQUIRY_TRIAGE


MAX_REPAIRS = 2


SYSTEM_PROMPT = """You design business automations for AutoFlow, a no-code workflow tool for small businesses.

Turn the user's request into a workflow definition that uses ONLY the actions in the catalogue below.

Definition format:
- "trigger": {"type": "manual" | "webhook" | "schedule" | "email" | "document", "schedule": "<cron, schedule only>", "connection": "<imap connection name, email only>", "sample_payload": {realistic example trigger data}}
  Choose the trigger that matches how the work starts:
  - "email": an email arrives in a mailbox. Trigger data: from, subject, text, attachments, attachments_text (text read from attached PDFs/scans). Set "connection" to a name such as "inbox".
  - "document": someone uploads a PDF, scan or photo. Trigger data: filename, text.
  - "webhook": another app (e.g. Shopify, a website form, a review app) sends data.
  - "schedule": at fixed times (cron, UTC).
  - "manual": the user starts it.
- "steps": ordered list. Each step: {"id": "snake_case_id", "name": "short label", "action": "<catalogue name>", "inputs": {...}, optional "when": {"left": ..., "op": "eq|neq|contains|exists|not_exists", "right": ...}, optional "retry": {"max_attempts": 1-5, "backoff_seconds": n}, optional "timeout_seconds": 1-300}
- Inputs may reference data with "{{trigger.<field>}}" or "{{steps.<earlier_step_id>.output.<field>}}". Only reference earlier steps and outputs the catalogue lists.
- Provide every required input of each action, and no inputs the action does not declare.
- Actions marked requires_approval always pause for a human; never try to disable that.
- Give network actions a retry policy.

If the request needs an app or capability that is not in the catalogue, do not invent actions: list it in "unsupported" and draft what is possible.
If essential details are missing, ask short questions in "questions". Make sensible assumptions for minor details and list them in "assumptions".

Reply with one JSON object only, no other text:
{"name": "...", "description": "...", "definition": {...} or null, "questions": [...], "assumptions": [...], "unsupported": [...]}"""


@dataclass
class DraftResult:
    name: str
    description: str
    definition: dict | None
    questions: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)
    provider: str = ""
    attempts: int = 0

    @property
    def status(self):
        return "ready" if self.definition is not None else "needs_details"


class DraftFailed(Exception):
    """The AI could not produce a valid workflow."""


def build_prompt(request_text, answers=None):
    catalogue = json.dumps(describe_actions(), indent=1)
    example = json.dumps(ENQUIRY_TRIAGE["definition"], indent=1)

    parts = [
        f"Action catalogue:\n{catalogue}",
        f"Example of a valid definition:\n{example}",
        f"User request:\n{request_text.strip()}",
    ]

    if answers:
        answered = "\n".join(f"Q: {a['question']}\nA: {a['answer']}" for a in answers)
        parts.append(f"Answers to your earlier questions:\n{answered}")

    return "\n\n".join(parts)


def _validate(reply):
    """Return (definition or None, error message or None)."""

    definition = reply.get("definition")

    if definition is None:
        return None, None

    try:
        validated = WorkflowDefinition.model_validate(definition)
    except ValidationError as error:
        problems = "; ".join(e["msg"] for e in error.errors())
        return None, problems

    return validated.model_dump(mode="json", exclude_none=True), None


def draft_workflow(request_text, answers=None):
    """Ask the AI for a workflow draft; repair it until it validates."""

    prompt = build_prompt(request_text, answers)
    last_problem = None

    for attempt in range(1, MAX_REPAIRS + 2):
        text, provider = providers.complete(SYSTEM_PROMPT, prompt)

        try:
            reply = extract_json(text)
            definition, problem = _validate(reply)
        except (ValueError, AttributeError) as error:
            reply, definition, problem = {}, None, f"Invalid JSON: {error}"

        if problem is None:
            return DraftResult(
                name=str(reply.get("name") or "New workflow")[:200],
                description=str(reply.get("description") or ""),
                definition=definition,
                questions=[str(q) for q in reply.get("questions") or []],
                assumptions=[str(a) for a in reply.get("assumptions") or []],
                unsupported=[str(u) for u in reply.get("unsupported") or []],
                provider=provider,
                attempts=attempt,
            )

        last_problem = problem
        prompt = (
            f"{prompt}\n\nYour previous reply:\n{text}\n\n"
            f"It was rejected by the validator: {problem}\n"
            f"Fix these problems and reply with the corrected JSON object only."
        )

    raise DraftFailed(f"The AI could not produce a valid workflow: {last_problem}")
