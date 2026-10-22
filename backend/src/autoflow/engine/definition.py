"""
The workflow definition format: a trigger plus an ordered list of steps.

Example:

    {
      "trigger": {"type": "manual"},
      "steps": [
        {"id": "classify", "action": "classify_enquiry",
         "inputs": {"message": "{{trigger.message}}"}},
        {"id": "quote", "action": "exchange_rate_quote",
         "inputs": {"amount_eur": 100},
         "when": {"left": "{{steps.classify.output.category}}", "op": "eq", "right": "Sales"},
         "retry": {"max_attempts": 3, "backoff_seconds": 2}}
      ]
    }

Definitions are validated before they are saved, so the engine only ever
runs workflows whose actions, inputs and references are known to be valid.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from autoflow.engine.actions import get_action
from autoflow.engine.templating import find_references


class Condition(BaseModel):
    left: Any
    op: Literal["eq", "neq", "contains", "exists", "not_exists"]
    right: Any = None


class RetryPolicy(BaseModel):
    max_attempts: int = Field(1, ge=1, le=5)
    backoff_seconds: float = Field(1.0, ge=0, le=60)


class Step(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,49}$")
    name: str | None = None
    action: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    when: Condition | None = None
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    timeout_seconds: int = Field(30, ge=1, le=300)
    # None = the action's default. Approval can be added, never removed
    # from actions that require it.
    requires_approval: bool | None = None

    def needs_approval(self):
        action = get_action(self.action)
        return bool(self.requires_approval or (action and action.requires_approval))


class Trigger(BaseModel):
    type: Literal["manual", "webhook", "schedule"] = "manual"
    schedule: str | None = Field(None, description="Cron expression for schedule triggers")
    sample_payload: dict[str, Any] = Field(
        default_factory=dict, description="Example trigger data used for test runs"
    )


class WorkflowDefinition(BaseModel):
    trigger: Trigger = Field(default_factory=Trigger)
    steps: list[Step] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def check_steps(self):
        seen = set()

        for step in self.steps:
            if step.id in seen:
                raise ValueError(f"Duplicate step id: {step.id}")

            action = get_action(step.action)
            if action is None:
                raise ValueError(f"Step {step.id}: unknown action {step.action}")

            if action.requires_approval and step.requires_approval is False:
                raise ValueError(
                    f"Step {step.id}: {step.action} always requires human approval"
                )

            unknown = set(step.inputs) - set(action.inputs)
            if unknown:
                raise ValueError(
                    f"Step {step.id}: unknown inputs {', '.join(sorted(unknown))}"
                )

            missing = [
                name
                for name, spec in action.inputs.items()
                if spec.required and name not in step.inputs
            ]
            if missing:
                raise ValueError(
                    f"Step {step.id}: missing inputs {', '.join(missing)}"
                )

            references = list(find_references(step.inputs))
            if step.when is not None:
                references += list(find_references(step.when.model_dump()))

            for reference in references:
                _check_reference(step.id, reference, seen)

            seen.add(step.id)

        if self.trigger.type == "schedule" and not self.trigger.schedule:
            raise ValueError("Schedule triggers need a cron expression")

        return self


def _check_reference(step_id, reference, earlier_steps):
    parts = reference.split(".")

    if parts[0] == "trigger":
        return

    if (
        len(parts) >= 3
        and parts[0] == "steps"
        and parts[2] == "output"
        and parts[1] in earlier_steps
    ):
        return

    raise ValueError(
        f"Step {step_id}: reference {{{{{reference}}}}} must point to the "
        f"trigger or an earlier step's output"
    )
