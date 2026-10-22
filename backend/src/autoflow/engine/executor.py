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
from datetime import datetime, timedelta

from autoflow import config
from autoflow.billing import service as billing
from autoflow.engine import limits
from autoflow.engine.actions import ActionContext, ActionError, delay_seconds, get_action, validate_inputs
from autoflow.engine.definition import WorkflowDefinition
from autoflow.engine.templating import evaluate_condition, render
from autoflow.storage.db import utc_now
from autoflow.storage.models import Approval, StepExecution, Workspace


TERMINAL_STATUSES = {"succeeded", "failed", "cancelled", "needs_attention"}

# Longest wait between retry attempts (keeps heartbeats frequent)
MAX_BACKOFF_SECONDS = 300

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

    if action.connection_provider and inputs.get("connection"):
        ctx.credentials = _load_credentials(ctx, action, inputs["connection"])

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


def _load_credentials(ctx, action, connection_name):
    """Decrypt this workspace's connection (main thread, has the session)."""

    from autoflow.integrations import connections

    try:
        config, secrets = connections.credentials_for(
            ctx.session, ctx.workspace_id, connection_name, action.connection_provider
        )
    except connections.ReconnectNeeded as error:
        raise ActionError(str(error), retryable=False) from error

    return {"config": config, "secrets": secrets}


def execute(session, execution):
    """Run (or continue) an execution until it finishes or must wait."""

    if execution.status in TERMINAL_STATUSES:
        return execution

    definition = WorkflowDefinition.model_validate(execution.version.definition)
    context = {"trigger": execution.trigger_payload, "steps": {}}
    workspace = session.get(Workspace, execution.workspace_id)

    execution.status = "running"
    execution.started_at = execution.started_at or utc_now()
    execution.heartbeat_at = utc_now()
    execution.run_after = None
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

        if action.name == "delay":
            if not _delay_elapsed(session, execution, step, record, inputs):
                return execution
            context["steps"][step.id] = {"output": record.output}
            continue

        needs_approval = step.needs_approval() or (
            workspace.approve_all_side_effects and action.side_effect
        )

        if execution.mode == "live" and needs_approval and record.status != "approved":
            _request_approval(session, execution, step, record, inputs)
            return execution

        try:
            limits.check_can_run_step(session, workspace, action.name, execution.mode)
            if billing.is_billable(action, execution.mode):
                billing.check_can_run_billable(session, workspace.id)
        except (limits.LimitReached, billing.PlanLimitReached) as limit:
            record.status = "failed"
            record.error = str(limit)
            _finish(session, execution, "failed", f"Step {step.id} stopped: {limit}")
            return execution

        if not _run_step(session, execution, step, record, action, inputs):
            return execution

        context["steps"][step.id] = {"output": record.output}

    _finish(session, execution, "succeeded")
    return execution


def _delay_elapsed(session, execution, step, record, inputs):
    """Handle a delay step. Returns True once the wait is over.

    The first time, the execution is parked as "queued" with run_after set
    to the resume time; a worker continues it then. Test runs skip waits.
    """

    if execution.mode == "test":
        record.status = "succeeded"
        record.output = {"skipped_in_test": True}
        record.finished_at = utc_now()
        session.commit()
        return True

    resume_at = (record.output or {}).get("resume_at")

    if resume_at is None:
        try:
            seconds = delay_seconds(inputs)
        except ActionError as error:
            record.status = "failed"
            record.error = str(error)
            _finish(session, execution, "failed", f"Step {step.id} failed: {error}")
            return False

        resume = utc_now() + timedelta(seconds=seconds)
        record.output = {"resume_at": resume.isoformat()}
        record.started_at = utc_now()
    else:
        resume = datetime.fromisoformat(resume_at)

    if utc_now() >= resume:
        record.status = "succeeded"
        record.finished_at = utc_now()
        session.commit()
        return True

    record.status = "waiting"
    execution.status = "queued"
    execution.run_after = resume
    execution.claimed_by = None
    session.commit()
    return False


def _request_approval(session, execution, step, record, inputs, review=None):
    """Pause the execution until a human decides.

    Without `review` this gates the step before it runs. With `review`
    ({"reason", "output"}) the step already ran and a person checks (and
    may correct) its output before the workflow continues.
    """

    record.status = "waiting_approval"
    payload = {
        "execution_id": execution.id,
        "step_id": step.id,
        "step_name": step.name or step.id,
        "action": step.action,
        "inputs": inputs,
    }
    if review is not None:
        payload.update({"review": True, **review})

    existing = session.query(Approval).filter_by(
        execution_id=execution.id, step_id=step.id
    ).first()

    if existing is None:
        session.add(Approval(
            workspace_id=execution.workspace_id,
            kind="step",
            customer_email=str(inputs.get("to") or inputs.get("email") or ""),
            payload=payload,
            execution_id=execution.id,
            step_id=step.id,
        ))
    elif existing.status != "pending":
        # The step was approved to run; now its result needs a review too
        payload["previous_decision"] = existing.decision
        existing.payload = payload
        existing.status = "pending"
        existing.decision = None
        existing.decided_at = None
        existing.decided_by_user_id = None

    execution.status = "waiting_approval"
    session.commit()


def _review_reason(step, output):
    """Why a live AI result must be checked by a person (None if not)."""

    if output.get("injection_suspected"):
        return "The input may contain a prompt-injection attempt."

    threshold = step.review_threshold()
    confidence = output.get("confidence")

    if threshold and isinstance(confidence, (int, float)) and confidence < threshold:
        return f"Confidence {confidence:.2f} is below the review threshold {threshold:.2f}."

    return None


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
        execution.heartbeat_at = utc_now()
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
            record.output = output if isinstance(output, dict) else {"result": output}
            reason = _review_reason(step, record.output) if execution.mode == "live" else None

            if reason:
                _request_approval(
                    session, execution, step, record, inputs,
                    review={"reason": reason, "output": record.output},
                )
                return False

            record.status = "succeeded"
            record.finished_at = utc_now()
            if billing.is_billable(action, execution.mode, record.output):
                # Same commit as the success, so it is counted exactly once
                billing.record_billable(session, execution.workspace_id, record, action.name)
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
        # Capped so the execution's heartbeat never goes quiet for long
        sleep(min(MAX_BACKOFF_SECONDS, step.retry.backoff_seconds * 2 ** (record.attempts - 1)))


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

    return _continue(session, execution)


def _continue(session, execution):
    """Run now (inline mode) or hand the execution to the workers (queue mode)."""

    if config.execution_mode() == "queue":
        execution.status = "queued"
        execution.claimed_by = None
        session.commit()
        return execution

    return execute(session, execution)


def resume_after_decision(session, execution, step_id, approved, review=False, corrected_output=None):
    """Continue (approved) or stop (rejected) after a step approval.

    For a review, approving accepts the step's output (or the reviewer's
    corrected output) and the workflow continues after that step.
    """

    record = next(r for r in execution.steps if r.step_id == step_id)

    if not approved:
        record.status = "rejected"
        record.finished_at = utc_now()
    elif review:
        if corrected_output is not None:
            record.output = {**(record.output or {}), **corrected_output, "reviewed": True}
        else:
            record.output = {**(record.output or {}), "reviewed": True}
        record.status = "succeeded"
        record.finished_at = utc_now()
    else:
        record.status = "approved"

    session.commit()
    return _continue(session, execution)
