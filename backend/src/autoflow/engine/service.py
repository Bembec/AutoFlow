"""
Workflows, versions and starting executions, scoped to one workspace.

Lifecycle: a workflow is created as a draft (version 1). Edits change the
draft. Publishing freezes the draft as the live version; editing again
starts a new draft. Any earlier version can be re-published (rollback).
Test runs use the draft (or the live version if there is no draft) and
simulate side effects. Live runs always use the published version.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from autoflow import config
from autoflow.billing import service as billing
from autoflow.engine import executor, limits
from autoflow.engine.definition import WorkflowDefinition
from autoflow.storage.db import utc_now
from autoflow.storage.models import Workflow, WorkflowExecution, WorkflowVersion


class WorkflowError(Exception):
    """A workflow request that cannot be completed."""


class NotFound(Exception):
    """Nothing with that id exists in this workspace."""


def _definition_json(definition):
    if not isinstance(definition, WorkflowDefinition):
        definition = WorkflowDefinition.model_validate(definition)
    return definition.model_dump(mode="json", exclude_none=True)


def list_workflows(session, workspace_id, include_archived=False):
    query = select(Workflow).where(Workflow.workspace_id == workspace_id)

    if not include_archived:
        query = query.where(Workflow.status != "archived")

    return session.scalars(query.order_by(Workflow.id)).all()


def get_workflow(session, workspace_id, workflow_id):
    workflow = session.scalar(
        select(Workflow).where(
            Workflow.workspace_id == workspace_id, Workflow.id == workflow_id
        )
    )

    if workflow is None:
        raise NotFound(workflow_id)

    return workflow


def version_in_state(workflow, state):
    return next((v for v in workflow.versions if v.state == state), None)


def create_workflow(
    session, workspace_id, name, definition, description="", user_id=None, minutes_saved_per_run=5,
    source_template=None,
):
    try:
        billing.check_can_create_workflow(session, workspace_id)
    except billing.PlanLimitReached as limit:
        raise WorkflowError(str(limit)) from limit

    workflow = Workflow(
        workspace_id=workspace_id,
        name=name,
        description=description,
        created_by_user_id=user_id,
        minutes_saved_per_run=minutes_saved_per_run,
        source_template=source_template,
    )
    workflow.versions.append(
        WorkflowVersion(number=1, state="draft", definition=_definition_json(definition))
    )
    session.add(workflow)
    session.commit()
    return workflow


def update_workflow(
    session, workspace_id, workflow_id, name=None, description=None, definition=None,
    minutes_saved_per_run=None, mcp_enabled=None,
):
    workflow = get_workflow(session, workspace_id, workflow_id)

    if workflow.status == "archived":
        raise WorkflowError("Archived workflows cannot be edited.")

    if name is not None:
        workflow.name = name
    if description is not None:
        workflow.description = description
    if minutes_saved_per_run is not None:
        workflow.minutes_saved_per_run = minutes_saved_per_run
    if mcp_enabled is not None:
        workflow.mcp_enabled = mcp_enabled

    if definition is not None:
        draft = version_in_state(workflow, "draft")

        if draft is None:
            # The published version stays frozen; edits start a new draft
            draft = WorkflowVersion(
                number=max(v.number for v in workflow.versions) + 1,
                state="draft",
                definition={},
            )
            workflow.versions.append(draft)

        draft.definition = _definition_json(definition)

    workflow.updated_at = utc_now()
    session.commit()
    return workflow


def publish(session, workspace_id, workflow_id, version_number=None):
    """Publish the draft, or re-publish an earlier version (rollback)."""

    workflow = get_workflow(session, workspace_id, workflow_id)

    if workflow.status == "archived":
        raise WorkflowError("Archived workflows cannot be published.")

    if version_number is None:
        target = version_in_state(workflow, "draft")
        if target is None:
            raise WorkflowError("There is no draft to publish.")
    else:
        target = next((v for v in workflow.versions if v.number == version_number), None)
        if target is None:
            raise NotFound(version_number)

    # Re-validate: actions may have changed since the version was saved
    WorkflowDefinition.model_validate(target.definition)

    current = version_in_state(workflow, "published")
    if current is not None and current is not target:
        current.state = "archived"

    target.state = "published"
    target.published_at = utc_now()
    workflow.updated_at = utc_now()
    session.commit()
    return workflow


def archive(session, workspace_id, workflow_id):
    workflow = get_workflow(session, workspace_id, workflow_id)
    workflow.status = "archived"
    session.commit()
    return workflow


def _cancel_open_executions(session, workspace_id, workflow_id=None, reason="Stopped"):
    query = select(WorkflowExecution).where(
        WorkflowExecution.workspace_id == workspace_id,
        WorkflowExecution.status.not_in(executor.TERMINAL_STATUSES),
    )
    if workflow_id is not None:
        query = query.where(WorkflowExecution.workflow_id == workflow_id)

    stopped = 0
    for execution in session.scalars(query).all():
        executor.cancel(session, execution)
        execution.error = reason
        stopped += 1

    session.commit()
    return stopped


def pause(session, workspace_id, workflow_id):
    """Emergency stop for one workflow: cancel its runs, refuse new live ones."""

    workflow = get_workflow(session, workspace_id, workflow_id)

    if workflow.status == "archived":
        raise WorkflowError("Archived workflows cannot be paused.")

    workflow.status = "paused"
    session.commit()
    _cancel_open_executions(session, workspace_id, workflow.id, "Workflow paused (emergency stop).")
    return workflow


def resume(session, workspace_id, workflow_id):
    workflow = get_workflow(session, workspace_id, workflow_id)

    if workflow.status != "paused":
        raise WorkflowError("Only paused workflows can be resumed.")

    workflow.status = "active"
    session.commit()
    return workflow


def emergency_stop(session, workspace_id, reason=None):
    """Stop every automation in a workspace at once."""

    workspace = limits.get_workspace(session, workspace_id)
    workspace.automation_paused = True
    workspace.paused_reason = reason or "Emergency stop"
    session.commit()
    return _cancel_open_executions(
        session, workspace_id, reason=f"Emergency stop: {workspace.paused_reason}"
    )


def resume_automations(session, workspace_id):
    workspace = limits.get_workspace(session, workspace_id)
    workspace.automation_paused = False
    workspace.paused_reason = None
    session.commit()
    return workspace


def get_execution(session, workspace_id, execution_id):
    execution = session.scalar(
        select(WorkflowExecution)
        .where(
            WorkflowExecution.workspace_id == workspace_id,
            WorkflowExecution.id == execution_id,
        )
        .execution_options(populate_existing=True)
    )

    if execution is None:
        raise NotFound(execution_id)

    return execution


def list_executions(session, workspace_id, workflow_id=None, status=None, limit=20):
    query = select(WorkflowExecution).where(WorkflowExecution.workspace_id == workspace_id)

    if workflow_id is not None:
        query = query.where(WorkflowExecution.workflow_id == workflow_id)
    if status is not None:
        query = query.where(WorkflowExecution.status == status)

    return session.scalars(query.order_by(WorkflowExecution.id.desc()).limit(limit)).all()


def start_execution(
    session,
    workspace_id,
    workflow_id,
    mode="live",
    payload=None,
    idempotency_key=None,
    user_id=None,
):
    """Create and run an execution. The same idempotency key returns the
    existing execution instead of starting another one."""

    if idempotency_key:
        existing = session.scalar(
            select(WorkflowExecution).where(
                WorkflowExecution.workspace_id == workspace_id,
                WorkflowExecution.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            return existing, False

    workflow = get_workflow(session, workspace_id, workflow_id)
    workspace = limits.get_workspace(session, workspace_id)

    if workflow.status == "archived":
        raise WorkflowError("Archived workflows cannot run.")

    if workspace.automation_paused:
        raise WorkflowError(
            f"Automations are stopped for this workspace: {workspace.paused_reason or 'emergency stop'}."
        )

    if workflow.status == "paused" and mode == "live":
        raise WorkflowError("This workflow is paused.")

    try:
        limits.check_can_start(session, workspace)
    except limits.LimitReached as limit:
        raise WorkflowError(str(limit)) from limit

    if mode == "live":
        version = version_in_state(workflow, "published")
        if version is None:
            raise WorkflowError("Publish the workflow before running it live.")
    else:
        version = version_in_state(workflow, "draft") or version_in_state(workflow, "published")

    if payload is None:
        payload = WorkflowDefinition.model_validate(version.definition).trigger.sample_payload

    execution = WorkflowExecution(
        workspace_id=workspace_id,
        workflow_id=workflow.id,
        version_id=version.id,
        mode=mode,
        trigger_payload=payload,
        idempotency_key=idempotency_key,
        triggered_by_user_id=user_id,
    )
    session.add(execution)

    try:
        session.commit()
    except IntegrityError:
        # Another request with the same key won the race
        session.rollback()
        return start_execution(session, workspace_id, workflow_id, mode, payload, idempotency_key, user_id)

    if config.execution_mode() != "queue":
        executor.execute(session, execution)

    return execution, True
