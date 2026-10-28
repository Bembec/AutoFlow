"""
Owner notifications: tell the business when something needs them.

Events (approval waiting, run failed or needs attention) are queued as
Notification rows in the same transaction as the event, and the worker
delivers them by email (the workspace's own SMTP connection) and/or
Slack. Delivery problems never affect workflows; failed sends are
retried up to MAX_ATTEMPTS times.
"""

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

import requests
from sqlalchemy import select

from autoflow import config
from autoflow.integrations import connections
from autoflow.storage.db import utc_now
from autoflow.storage.models import Notification, Workspace


logger = logging.getLogger("autoflow.notifications")

MAX_ATTEMPTS = 5
BATCH = 50


def enqueue(session, workspace_id, kind, subject, body, link=None):
    """Queue a notification if the workspace wants this kind. Not committed here."""

    workspace = session.get(Workspace, workspace_id)
    if workspace is None:
        return None

    wanted = {"approval": workspace.notify_on_approval, "failure": workspace.notify_on_failure}.get(kind, True)
    has_channel = workspace.notify_slack_connection or (workspace.notify_email and workspace.notify_smtp_connection)
    if not wanted or not has_channel:
        return None

    notification = Notification(
        workspace_id=workspace_id,
        kind=kind,
        subject=subject[:300],
        body=body,
        link=f"{config.PUBLIC_URL}{link}" if link else None,
    )
    session.add(notification)
    return notification


def _send_email(session, workspace, notification):
    if os.getenv("EMAIL_SEND_ENABLED", "false").lower() != "true":
        raise RuntimeError("Email sending is disabled on this server (EMAIL_SEND_ENABLED).")

    smtp_config, secrets = connections.credentials_for(
        session, workspace.id, workspace.notify_smtp_connection, "smtp"
    )
    message = EmailMessage()
    message["From"] = smtp_config["from_address"]
    message["To"] = workspace.notify_email
    message["Subject"] = f"[Luphina] {notification.subject}"
    message.set_content(notification.body + (f"\n\nOpen: {notification.link}" if notification.link else ""))

    with smtplib.SMTP_SSL(
        smtp_config["host"], int(smtp_config.get("port") or 465), context=ssl.create_default_context(), timeout=20
    ) as server:
        server.login(smtp_config["username"], secrets["password"])
        server.send_message(message)


def _send_slack(session, workspace, notification):
    _, secrets = connections.credentials_for(session, workspace.id, workspace.notify_slack_connection, "slack")
    url = secrets["webhook_url"]
    if not url.startswith(connections.SLACK_WEBHOOK_PREFIX):
        raise RuntimeError("Invalid Slack webhook URL.")

    text = f"*{notification.subject}*\n{notification.body}"
    if notification.link:
        text += f"\n<{notification.link}|Open in Luphina>"

    response = requests.post(url, json={"text": text}, timeout=15, allow_redirects=False)
    if response.status_code >= 400:
        raise RuntimeError(f"Slack returned {response.status_code}")


def deliver_pending(session):
    """Send queued notifications. Returns how many were delivered."""

    pending = session.scalars(
        select(Notification)
        .where(Notification.sent_at.is_(None), Notification.attempts < MAX_ATTEMPTS)
        .order_by(Notification.id)
        .limit(BATCH)
    ).all()

    delivered = 0
    for notification in pending:
        workspace = session.get(Workspace, notification.workspace_id)
        notification.attempts += 1
        errors = []

        channels = []
        if workspace.notify_slack_connection:
            channels.append(_send_slack)
        if workspace.notify_email and workspace.notify_smtp_connection:
            channels.append(_send_email)

        for send in channels:
            try:
                send(session, workspace, notification)
            except Exception as error:  # noqa: BLE001 - delivery problems must not stop the worker
                errors.append(f"{send.__name__.removeprefix('_send_')}: {error}")

        # Delivered when at least one channel worked
        if channels and len(errors) < len(channels):
            notification.sent_at = utc_now()
            delivered += 1
        notification.last_error = "; ".join(errors) or None
        session.commit()

        if errors:
            logger.warning("Notification %s: %s", notification.id, notification.last_error)

    return delivered
