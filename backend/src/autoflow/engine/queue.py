"""
Background execution queue.

With AUTOFLOW_EXECUTION_MODE=queue, starting a workflow only records a
"queued" execution and returns; workers run it. Executions waiting on a
delay step are also "queued", with `run_after` set to when they resume.

Claiming is a conditional UPDATE (status must still be "queued"), so two
workers can never run the same execution. Running executions send a
heartbeat; if a worker dies, its executions are re-queued after
STALE_AFTER and resumed. The executor's own rules then make sure an
uncertain side effect is never repeated blindly (needs_attention).
"""

import os
from datetime import timedelta

from sqlalchemy import func, or_, select, update

from autoflow.engine import executor
from autoflow.storage.db import utc_now
from autoflow.storage.models import WorkflowExecution


STALE_AFTER = timedelta(minutes=int(os.getenv("AUTOFLOW_STALE_EXECUTION_MINUTES", "15")))


def claim_next(session, worker_id, now=None):
    """Claim the oldest due queued execution, or return None."""

    now = now or utc_now()

    candidates = session.scalars(
        select(WorkflowExecution.id)
        .where(
            WorkflowExecution.status == "queued",
            or_(WorkflowExecution.run_after.is_(None), WorkflowExecution.run_after <= now),
        )
        .order_by(func.coalesce(WorkflowExecution.run_after, WorkflowExecution.created_at))
        .limit(5)
    ).all()

    for execution_id in candidates:
        claimed = session.execute(
            update(WorkflowExecution)
            .where(WorkflowExecution.id == execution_id, WorkflowExecution.status == "queued")
            .values(status="running", claimed_by=worker_id, heartbeat_at=now)
            .execution_options(synchronize_session=False)
        ).rowcount
        session.commit()

        if claimed == 1:
            return session.scalar(
                select(WorkflowExecution)
                .where(WorkflowExecution.id == execution_id)
                .execution_options(populate_existing=True)
            )

    return None


def run_due(session, worker_id, limit=10):
    """Run up to `limit` due executions. Returns how many were run."""

    ran = 0
    while ran < limit:
        execution = claim_next(session, worker_id)
        if execution is None:
            break
        executor.execute(session, execution)
        ran += 1
    return ran


def recover_stale(session, now=None):
    """Re-queue executions whose worker stopped sending heartbeats."""

    now = now or utc_now()
    cutoff = now - STALE_AFTER

    result = session.execute(
        update(WorkflowExecution)
        .where(
            WorkflowExecution.status == "running",
            func.coalesce(WorkflowExecution.heartbeat_at, WorkflowExecution.started_at) < cutoff,
        )
        .values(status="queued", claimed_by=None, run_after=None)
        .execution_options(synchronize_session=False)
    )
    session.commit()
    return result.rowcount
