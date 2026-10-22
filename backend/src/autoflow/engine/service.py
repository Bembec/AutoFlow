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

from autoflow.engine import executor
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
        query = query.where(Workflow.status == "active")

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


def create_workflow(session, workspace_id, name, definition, description="", user_id=None):
    workflow = Workflow(
        workspace_id=workspace_id,
        name=name,
        description=description,
        created_by_user_id=user_id,
    )
    workflow.versions.append(
        WorkflowVersion(number=1, state="draft", definition=_definition_json(definition))
    )
    session.add(workflow)
    session.commit()
    return workflow


def update_workflow(session, workspace_id, workflow_id, name=None, description=None, definition=None):
    workflow = get_workflow(session, workspace_id, workflow_id)

    if workflow.status == "archived":
        raise WorkflowError("Archived workflows cannot be edited.")

    if name is not None:
        workflow.name = name
    if description is not None:
        workflow.description = description

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

    if workflow.status == "archived":
        raise WorkflowError("Archived workflows cannot run.")

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

    executor.execute(session, execution)
    return execution, True
