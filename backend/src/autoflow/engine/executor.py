"""
Runs workflow executions step by step, reliably.

Guarantees:
- A step that already succeeded is never run again (resume and retry
  continue from where the execution stopped).
- A step is marked "running" and committed *before* its action starts.
  If a non-idempotent side effect (e.g. sending an email) is found still
  "running" or timed out, its outcome is unknown, so the execution stops
  with status needs_attention instead of risking a duplicate.
- Live side effects that need approval wait for a human decision.
- Test executions simulate side effects, so nothing real happens.
- Cancelling is checked before every step.

Executions currently run in the calling process. The same functions can
later be driven by a background worker or a durable engine (Temporal).
"""

import time
from concurrent.futures import ThreadPoolExecutor

from autoflow.engine.actions import ActionContext, ActionError, get_action, validate_inputs
from autoflow.engine.definition import WorkflowDefinition
from autoflow.engine.templating import evaluate_condition, render
from autoflow.storage.db import utc_now
from autoflow.storage.models import Approval, StepExecution


TERMINAL_STATUSES = {"succeeded", "failed", "cancelled", "needs_attention"}

# Replaced in tests so retries do not really wait
sleep = time.sleep


class ExecutionConflict(Exception):
    """The execution cannot do what was asked in its current state."""


def _finish(session, execution, status, error=None):
    execution.status = status
    execution.error = error
    execution.finished_at = utc_now()
    session.commit()


def _step_record(session, execution, step, position):
    for record in execution.steps:
        if record.step_id == step.id:
            return record

    record = StepExecution(
        execution_id=execution.id,
        step_id=step.id,
        position=position,
        action=step.action,
    )
    session.add(record)
    execution.steps.append(record)
    session.flush()
    return record


def _invoke(action, ctx, inputs, timeout_seconds):
    validate_inputs(action, inputs)

    if ctx.mode == "test" and action.side_effect:
        if action.simulate is not None:
            return action.simulate(ctx, inputs)
        return {"dry_run": True}

    if not action.uses_network:
        return action.handler(ctx, inputs)

    # Network actions run in a worker thread so a timeout can apply.
    # They never receive the database session.
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        thread_ctx = ActionContext(**{**ctx.__dict__, "session": None})
        future = pool.submit(action.handler, thread_ctx, inputs)
        return future.result(timeout=timeout_seconds)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def execute(session, execution):
    """Run (or continue) an execution until it finishes or must wait."""

    if execution.status in TERMINAL_STATUSES:
        return execution

    definition = WorkflowDefinition.model_validate(execution.version.definition)
    context = {"trigger": execution.trigger_payload, "steps": {}}

    execution.status = "running"
    execution.started_at = execution.started_at or utc_now()
    session.commit()

    for position, step in enumerate(definition.steps):
        # Stop at once if someone cancelled the execution
        session.refresh(execution, ["status"])
        if execution.status == "cancelled":
            return execution

        record = _step_record(session, execution, step, position)
        action = get_action(step.action)

        if record.status in ("succeeded", "skipped"):
            context["steps"][step.id] = {"output": record.output}
            continue

        if record.status == "rejected":
            _finish(session, execution, "cancelled", f"Step {step.id} was rejected by a reviewer.")
            return execution

        if record.status == "running" and action.side_effect and not action.idempotent:
            record.status = "failed"
            record.error = "Interrupted while running; the outcome is unknown."
            _finish(
                session,
                execution,
                "needs_attention",
                f"Step {step.id} may or may not have completed. Check before retrying.",
            )
            return execution

        if step.when is not None and not evaluate_condition(step.when, context):
            record.status = "skipped"
            record.output = None
            record.finished_at = utc_now()
            session.commit()
            context["steps"][step.id] = {"output": None}
            continue

        inputs = render(step.inputs, context)
        record.input = inputs

        if (
            execution.mode == "live"
            and step.needs_approval()
            and record.status != "approved"
        ):
            _request_approval(session, execution, step, record, inputs)
            return execution

        if not _run_step(session, execution, step, record, action, inputs):
            return execution

        context["steps"][step.id] = {"output": record.output}

    _finish(session, execution, "succeeded")
    return execution


def _request_approval(session, execution, step, record, inputs):
    record.status = "waiting_approval"

    existing = next(
        (
            approval
            for approval in session.query(Approval).filter_by(
                execution_id=execution.id, step_id=step.id
            )
        ),
        None,
    )

    if existing is None:
        session.add(Approval(
            workspace_id=execution.workspace_id,
            kind="step",
            customer_email=str(inputs.get("to") or inputs.get("email") or ""),
            payload={
                "execution_id": execution.id,
                "step_id": step.id,
                "step_name": step.name or step.id,
                "action": step.action,
                "inputs": inputs,
            },
            execution_id=execution.id,
            step_id=step.id,
        ))

    execution.status = "waiting_approval"
    session.commit()


def _run_step(session, execution, step, record, action, inputs):
    """Run one step with retries. Returns True if the execution may continue."""

    ctx = ActionContext(
        workspace_id=execution.workspace_id,
        execution_id=execution.id,
        step_id=step.id,
        idempotency_key=f"execution-{execution.id}-step-{step.id}",
        mode=execution.mode,
        session=session,
    )

    while True:
        # Record the attempt before acting, so a crash is detectable
        record.attempts += 1
        record.status = "running"
        record.error = None
        record.started_at = utc_now()
        session.commit()

        try:
            output = _invoke(action, ctx, inputs, step.timeout_seconds)
        except TimeoutError:
            if action.side_effect and not action.idempotent and execution.mode == "live":
                record.status = "failed"
                record.error = f"Timed out after {step.timeout_seconds}s; the outcome is unknown."
                _finish(
                    session,
                    execution,
                    "needs_attention",
                    f"Step {step.id} timed out and may have completed. Check before retrying.",
                )
                return False
            error, retryable = f"Timed out after {step.timeout_seconds}s.", True
        except ActionError as action_error:
            error, retryable = str(action_error), action_error.retryable
        except Exception as unexpected:  # noqa: BLE001 - any action bug fails the step
            error, retryable = f"Unexpected error: {unexpected}", False
        else:
            record.status = "succeeded"
            record.output = output if isinstance(output, dict) else {"result": output}
            record.finished_at = utc_now()
            session.commit()
            return True

        if not retryable or record.attempts >= step.retry.max_attempts:
            record.status = "failed"
            record.error = error
            record.finished_at = utc_now()
            _finish(session, execution, "failed", f"Step {step.id} failed: {error}")
            return False

        record.error = error
        session.commit()
        sleep(step.retry.backoff_seconds * 2 ** (record.attempts - 1))


# --- operator actions -------------------------------------------------------

def cancel(session, execution):
    """Stop an execution; pending step approvals are withdrawn."""

    if execution.status in TERMINAL_STATUSES:
        raise ExecutionConflict(f"Execution is already {execution.status}.")

    for approval in session.query(Approval).filter_by(
        execution_id=execution.id, status="pending"
    ):
        approval.status = "cancelled"
        approval.decided_at = utc_now()

    _finish(session, execution, "cancelled", "Cancelled by a user.")
    return execution


def retry(session, execution, confirm_not_completed=False):
    """Continue a failed execution from the step that failed.

    For needs_attention executions the caller must confirm that the
    uncertain step did not complete, so it is never duplicated blindly.
    """

    if execution.status == "needs_attention" and not confirm_not_completed:
        raise ExecutionConflict(
            "Confirm the uncertain step did not complete before retrying."
        )

    if execution.status not in ("failed", "needs_attention"):
        raise ExecutionConflict(f"Only failed executions can be retried (status: {execution.status}).")

    for record in execution.steps:
        if record.status == "failed":
            # A step a human already approved keeps that approval
            already_approved = session.query(Approval).filter_by(
                execution_id=execution.id, step_id=record.step_id, status="approved"
            ).first()

            record.status = "approved" if already_approved else "pending"
            record.attempts = 0
            record.error = None

    execution.status = "queued"
    execution.error = None
    execution.finished_at = None
    session.commit()

    return execute(session, execution)


def resume_after_decision(session, execution, step_id, approved):
    """Continue (approved) or stop (rejected) after a step approval."""

    record = next(r for r in execution.steps if r.step_id == step_id)
    record.status = "approved" if approved else "rejected"

    if not approved:
        record.finished_at = utc_now()

    session.commit()
    return execute(session, execution)
