"""
Background worker: runs queued executions, scheduled workflows and
housekeeping. Run as many workers as needed.

    python -m autoflow.worker

- Every second it runs due queued executions (queue mode, and executions
  resuming after a delay step). Claims are atomic, so workers never run
  the same execution twice.
- Every TICK_SECONDS it starts each published, active workflow whose
  schedule trigger (cron, UTC) was due. Each due time gets the
  idempotency key "schedule:<workflow>:<time>", so restarts or several
  workers never start the same slot twice. It also re-queues executions
  whose worker died, and removes long-expired login tokens.
"""

import logging
import os
import signal
import socket
import time
from datetime import datetime, timedelta, timezone

from croniter import croniter
from sqlalchemy import delete, select

from autoflow import config
from autoflow.engine import queue
from autoflow.engine import service as engine
from autoflow.engine.definition import WorkflowDefinition
from autoflow.storage.db import session_scope, utc_now
from autoflow.storage.models import AccessToken, Workflow, Workspace


logger = logging.getLogger("autoflow.worker")

TICK_SECONDS = int(os.getenv("AUTOFLOW_WORKER_TICK_SECONDS", "30"))
# How far back a tick looks, so a short outage does not skip a slot
LOOKBACK = timedelta(minutes=int(os.getenv("AUTOFLOW_SCHEDULE_LOOKBACK_MINUTES", "10")))


def due_times(schedule, since, until):
    """Every time the cron schedule fired in (since, until]."""

    times = []
    iterator = croniter(schedule, since)
    while (moment := iterator.get_next(datetime)) <= until:
        times.append(moment)
    return times


def run_schedules(session, now=None):
    """Start every scheduled run that is due. Returns how many started."""

    now = now or datetime.now(timezone.utc)
    started = 0

    workflows = session.scalars(
        select(Workflow)
        .join(Workspace, Workspace.id == Workflow.workspace_id)
        .where(Workflow.status == "active", Workspace.automation_paused.is_(False))
    ).all()

    for workflow in workflows:
        published = engine.version_in_state(workflow, "published")
        if published is None:
            continue

        trigger = WorkflowDefinition.model_validate(published.definition).trigger
        if trigger.type != "schedule" or not trigger.schedule:
            continue

        for moment in due_times(trigger.schedule, now - LOOKBACK, now):
            key = f"schedule:{workflow.id}:{moment:%Y%m%dT%H%M}"
            try:
                _, created = engine.start_execution(
                    session,
                    workflow.workspace_id,
                    workflow.id,
                    mode="live",
                    payload={"scheduled_for": moment.isoformat(), **trigger.sample_payload},
                    idempotency_key=key,
                )
                started += created
            except engine.WorkflowError as error:
                logger.warning("Scheduled run of workflow %s skipped: %s", workflow.id, error)
                session.rollback()

    return started


def housekeeping(session):
    """Remove access tokens that expired more than a week ago."""

    session.execute(delete(AccessToken).where(AccessToken.expires_at < utc_now() - timedelta(days=7)))
    session.commit()


def main():
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    config.check_deployment_settings()

    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    worker_id = f"{socket.gethostname()}-{os.getpid()}"
    logger.info(
        "Worker %s started (tick %ss, execution mode %s, environment %s)",
        worker_id, TICK_SECONDS, config.execution_mode(), config.ENVIRONMENT,
    )
    next_tick = 0.0

    while not stopping:
        try:
            if time.monotonic() >= next_tick:
                next_tick = time.monotonic() + TICK_SECONDS
                with session_scope() as session:
                    recovered = queue.recover_stale(session)
                    started = run_schedules(session)
                    housekeeping(session)
                if recovered:
                    logger.warning("Re-queued %s execution(s) from a stopped worker", recovered)
                if started:
                    logger.info("Started %s scheduled run(s)", started)

            with session_scope() as session:
                ran = queue.run_due(session, worker_id)
            if ran:
                logger.info("Ran %s queued execution(s)", ran)
                continue  # more may be waiting
        except Exception:  # noqa: BLE001 - keep the worker alive; the next loop retries
            logger.exception("Worker loop failed")

        time.sleep(1)

    logger.info("Worker stopped")


if __name__ == "__main__":
    main()
