"""
Email triggers: the worker watches an IMAP mailbox and starts a workflow
run for each new message.

- Messages are fetched without marking them read; a message is marked
  read only after its run was created, so a crash never loses an email.
- Each run's idempotency key is the email's Message-ID, so a message is
  never processed twice (even if marking it read failed).
- Attachments (PDF, images, text) are read into text for AI steps.

Trigger data:
    {"from", "to", "subject", "date", "message_id", "text",
     "attachments": [{"filename", "content_type", "size", "text", "method"}],
     "attachments_text": "all attachment text, joined"}
"""

import email
import email.policy
import hashlib
import imaplib
import logging
import re
from html import unescape

from autoflow import documents
from autoflow.engine import service as engine
from autoflow.integrations import connections


logger = logging.getLogger("autoflow.email")

MAX_MESSAGES_PER_POLL = 20
MAX_ATTACHMENTS = 5


def _html_to_text(html):
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[ \t]+", " ", unescape(text)).strip()


def parse_message(raw, allow_ai=True):
    """Turn a raw email into trigger data."""

    message = email.message_from_bytes(raw, policy=email.policy.default)

    body = message.get_body(preferencelist=("plain", "html"))
    if body is None:
        text = ""
    elif body.get_content_type() == "text/html":
        text = _html_to_text(body.get_content())
    else:
        text = body.get_content()

    attachments = []
    for part in message.iter_attachments():
        if len(attachments) >= MAX_ATTACHMENTS:
            break
        data = part.get_payload(decode=True) or b""
        filename = part.get_filename() or "attachment"
        try:
            attachments.append(documents.extract_text(data, filename, allow_ai=allow_ai))
        except documents.DocumentError as error:
            attachments.append({"filename": filename, "size": len(data), "text": "", "error": str(error)})

    message_id = str(message.get("Message-ID") or "").strip()
    if not message_id:
        # Some senders omit it; derive a stable id from the content
        message_id = "sha256:" + hashlib.sha256(raw).hexdigest()

    return {
        "from": str(message.get("From") or ""),
        "to": str(message.get("To") or ""),
        "subject": str(message.get("Subject") or ""),
        "date": str(message.get("Date") or ""),
        "message_id": message_id,
        "text": text.strip()[: documents.MAX_TEXT_CHARS],
        "attachments": [{key: value for key, value in a.items()} for a in attachments],
        "attachments_text": "\n\n".join(
            f"--- {a['filename']} ---\n{a['text']}" for a in attachments if a.get("text")
        ),
    }


def _connect(config, secrets):
    client = imaplib.IMAP4_SSL(config["host"], int(config.get("port") or 993), timeout=30)
    client.login(config["username"], secrets["password"])
    return client


def poll_workflow(session, workflow, trigger):
    """Start runs for new messages in one workflow's mailbox. Returns how many started."""

    try:
        config, secrets = connections.credentials_for(
            session, workflow.workspace_id, trigger.connection, "imap"
        )
    except connections.ReconnectNeeded as error:
        logger.warning("Email trigger of workflow %s skipped: %s", workflow.id, error)
        return 0

    started = 0
    client = _connect(config, secrets)
    try:
        status, _ = client.select(trigger.folder)
        if status != "OK":
            logger.warning("Workflow %s: folder %r not found", workflow.id, trigger.folder)
            return 0

        _, found = client.uid("SEARCH", None, "UNSEEN")
        for uid in (found[0].split() if found and found[0] else [])[:MAX_MESSAGES_PER_POLL]:
            # PEEK: reading does not mark the message as seen
            _, fetched = client.uid("FETCH", uid, "(BODY.PEEK[])")
            raw = next((part[1] for part in fetched if isinstance(part, tuple)), None)
            if raw is None:
                continue

            payload = parse_message(raw)
            _, created = engine.start_execution(
                session,
                workflow.workspace_id,
                workflow.id,
                mode="live",
                payload=payload,
                idempotency_key=f"email:{workflow.id}:{payload['message_id']}"[:200],
            )
            started += created
            client.uid("STORE", uid, "+FLAGS", "(\\Seen)")
    finally:
        try:
            client.logout()
        except (imaplib.IMAP4.error, OSError):
            pass

    return started
