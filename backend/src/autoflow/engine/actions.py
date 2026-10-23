"""
The actions a workflow step can call.

Each action declares its inputs and outputs (used for validation and,
later, by the AI builder) and two safety flags:

- side_effect: it changes something outside the run (sends, saves).
  In test mode it is simulated instead of performed.
- idempotent: repeating it is harmless. A non-idempotent side effect whose
  outcome is unknown (e.g. a crash mid-send) is never retried automatically.
"""

from dataclasses import dataclass, field
from typing import Any, Callable

from autoflow.activity_log import timestamp_now, write_log_lines
from autoflow.classification.ai_classifier import classify_with_ai
from autoflow.emails.sender import send_email
from autoflow.emails.templates import create_email_preview
from autoflow.integrations.exchange_rates import fetch_eur_to_usd


class ActionError(Exception):
    """An action failed. Retryable errors are attempted again."""

    def __init__(self, message, retryable=True):
        super().__init__(message)
        self.retryable = retryable


@dataclass
class ActionContext:
    workspace_id: int
    execution_id: int
    step_id: str
    idempotency_key: str
    mode: str
    # Only provided to actions that run inline (not in a timeout thread)
    session: Any = None
    # Decrypted {"config", "secrets"} of the step's connection, if any
    credentials: dict | None = None


@dataclass
class InputSpec:
    type: str  # "string" | "number" | "boolean" | "any"
    required: bool = True
    description: str = ""


@dataclass
class Action:
    name: str
    description: str
    handler: Callable
    inputs: dict[str, InputSpec]
    outputs: dict[str, str]
    side_effect: bool = False
    idempotent: bool = True
    requires_approval: bool = False
    # Calls external services: run in a worker thread so a timeout can apply
    uses_network: bool = False
    simulate: Callable | None = field(default=None)
    # Provider whose connection (named in the "connection" input) this needs
    connection_provider: str | None = None
    # Live results with a lower `confidence` wait for human review
    review_below_confidence: float | None = None
    # Billing: None = billable when it uses the network; or a function of
    # the output, for actions that only sometimes call an app or AI model
    billable: Callable | None = None


REGISTRY: dict[str, Action] = {}


def register(action):
    REGISTRY[action.name] = action
    return action


def get_action(name):
    return REGISTRY.get(name)


TYPE_CHECKS = {
    "string": lambda value: isinstance(value, str),
    "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
    "boolean": lambda value: isinstance(value, bool),
    "any": lambda value: True,
}


def validate_inputs(action, inputs):
    """Raise a non-retryable ActionError if the inputs do not fit."""

    for name, spec in action.inputs.items():
        value = inputs.get(name)

        if value in (None, ""):
            if spec.required:
                raise ActionError(f"Missing required input: {name}", retryable=False)
            continue

        if not TYPE_CHECKS[spec.type](value):
            raise ActionError(
                f"Input {name} must be a {spec.type}, got {type(value).__name__}",
                retryable=False,
            )

    unknown = set(inputs) - set(action.inputs)
    if unknown:
        raise ActionError(f"Unknown inputs: {', '.join(sorted(unknown))}", retryable=False)


def describe_actions():
    """A JSON-friendly catalogue of every action (for the API and AI builder)."""

    return [
        {
            "name": action.name,
            "description": action.description,
            "inputs": {
                name: {
                    "type": spec.type,
                    "required": spec.required,
                    "description": spec.description,
                }
                for name, spec in action.inputs.items()
            },
            "outputs": action.outputs,
            "side_effect": action.side_effect,
            "requires_approval": action.requires_approval,
            "connection_provider": action.connection_provider,
        }
        for action in REGISTRY.values()
    ]


# --- built-in actions -------------------------------------------------------

def _classify_enquiry(ctx, inputs):
    message = inputs["message"].strip()
    ai_result = classify_with_ai(message)

    if ai_result is not None:
        return {**ai_result, "source": "AI"}

    lowered = message.lower()
    if "price" in lowered:
        category = "Sales"
    elif "help" in lowered:
        category = "Support"
    else:
        category = "Other"

    return {
        "category": category,
        "reason": "Classified using keyword rules.",
        "source": "Rules",
    }


register(Action(
    name="classify_enquiry",
    description="Classify a customer message as Sales, Support or Other (AI with keyword fallback).",
    handler=_classify_enquiry,
    inputs={"message": InputSpec("string", description="The customer's message")},
    outputs={"category": "Sales | Support | Other", "reason": "Why", "source": "AI | Rules"},
    uses_network=True,
    # Keyword rules run locally; only an AI classification is billable
    billable=lambda output: output.get("source") == "AI",
))


def _exchange_rate_quote(ctx, inputs):
    exchange_rate, rate_date = fetch_eur_to_usd()

    if exchange_rate is None:
        raise ActionError("Exchange rate unavailable.")

    amount_eur = float(inputs["amount_eur"])
    return {
        "amount_eur": f"{amount_eur:.2f}",
        "amount_usd": f"{amount_eur * exchange_rate:.2f}",
        "rate": exchange_rate,
        "rate_date": rate_date,
    }


register(Action(
    name="exchange_rate_quote",
    description="Convert a EUR amount to USD using today's reference rate.",
    handler=_exchange_rate_quote,
    inputs={"amount_eur": InputSpec("number", description="Amount in euros")},
    outputs={"amount_eur": "text", "amount_usd": "text", "rate": "number", "rate_date": "date"},
    uses_network=True,
))


def _compose_email(ctx, inputs):
    return create_email_preview({
        "name": inputs["name"],
        "email": inputs["email"],
        "category": inputs["category"],
        "quote_usd": inputs.get("quote_usd") or "",
    })


register(Action(
    name="compose_email",
    description="Write a personalised reply for a customer based on their category.",
    handler=_compose_email,
    inputs={
        "name": InputSpec("string"),
        "email": InputSpec("string"),
        "category": InputSpec("string", description="Sales | Support | Other"),
        "quote_usd": InputSpec("string", required=False),
    },
    outputs={"to": "email", "subject": "text", "body": "text"},
))


def _send_email(ctx, inputs):
    if not send_email({"to": inputs["to"], "subject": inputs["subject"], "body": inputs["body"]}):
        raise ActionError("Email was not sent (sending disabled or failed).")

    return {"sent": True, "to": inputs["to"]}


register(Action(
    name="send_email",
    description="Send an email to a customer (redirected to the test inbox during development).",
    handler=_send_email,
    inputs={
        "to": InputSpec("string"),
        "subject": InputSpec("string"),
        "body": InputSpec("string"),
    },
    outputs={"sent": "boolean", "to": "email"},
    side_effect=True,
    idempotent=False,
    requires_approval=True,
    uses_network=True,
    simulate=lambda ctx, inputs: {"sent": False, "to": inputs["to"], "dry_run": True},
))


def _save_customer(ctx, inputs):
    from autoflow.storage.customers import save_customers

    save_customers(ctx.session, ctx.workspace_id, [{
        "id": inputs.get("customer_id") or "",
        "name": inputs["name"],
        "email": inputs["email"],
        "message": inputs["message"],
        "category": inputs["category"],
        "classification_source": inputs.get("classification_source") or "Workflow",
        "classification_reason": inputs.get("classification_reason") or "",
        "quote_eur": inputs.get("quote_eur") or "",
        "quote_usd": inputs.get("quote_usd") or "",
        "rate_date": inputs.get("rate_date") or "",
    }])
    return {"saved": True, "email": inputs["email"].strip().lower()}


register(Action(
    name="save_customer",
    description="Create or update a customer record in this workspace (matched by email).",
    handler=_save_customer,
    inputs={
        "name": InputSpec("string"),
        "email": InputSpec("string"),
        "message": InputSpec("string"),
        "category": InputSpec("string"),
        "customer_id": InputSpec("string", required=False),
        "classification_source": InputSpec("string", required=False),
        "classification_reason": InputSpec("string", required=False),
        "quote_eur": InputSpec("string", required=False),
        "quote_usd": InputSpec("string", required=False),
        "rate_date": InputSpec("string", required=False),
    },
    outputs={"saved": "boolean", "email": "email"},
    side_effect=True,
    idempotent=True,
    simulate=lambda ctx, inputs: {"saved": False, "email": inputs["email"], "dry_run": True},
))


def _log_activity(ctx, inputs):
    write_log_lines([
        f"{timestamp_now()} | Workspace: {ctx.workspace_id} | "
        f"EXECUTION #{ctx.execution_id} | {ctx.step_id} | {inputs['message']}"
    ])
    return {"logged": True}


register(Action(
    name="log_activity",
    description="Write a line to the activity log.",
    handler=_log_activity,
    inputs={"message": InputSpec("string")},
    outputs={"logged": "boolean"},
    side_effect=True,
    idempotent=True,
))


MAX_DELAY_DAYS = 30


def _no_handler(ctx, inputs):  # pragma: no cover - the executor handles delays
    raise ActionError("Delay steps are run by the executor.", retryable=False)


register(Action(
    name="delay",
    description="Wait before the next step (e.g. follow up after 2 days). Needs the background worker.",
    handler=_no_handler,
    inputs={
        "minutes": InputSpec("number", required=False),
        "hours": InputSpec("number", required=False),
        "days": InputSpec("number", required=False, description=f"Up to {MAX_DELAY_DAYS} days in total"),
    },
    outputs={"resume_at": "date-time"},
))


def delay_seconds(inputs):
    """Total delay of a delay step, validated."""

    seconds = (
        float(inputs.get("minutes") or 0) * 60
        + float(inputs.get("hours") or 0) * 3600
        + float(inputs.get("days") or 0) * 86400
    )
    if seconds <= 0:
        raise ActionError("A delay needs minutes, hours or days greater than 0.", retryable=False)
    if seconds > MAX_DELAY_DAYS * 86400:
        raise ActionError(f"A delay can be at most {MAX_DELAY_DAYS} days.", retryable=False)
    return seconds


# Connector actions register themselves into the same registry
from autoflow.integrations import actions as _connector_actions  # noqa: E402,F401
from autoflow.ai import steps as _ai_steps  # noqa: E402,F401
from autoflow.ai import agent as _ai_agent  # noqa: E402,F401
from autoflow.commerce import actions as _commerce_actions  # noqa: E402,F401
