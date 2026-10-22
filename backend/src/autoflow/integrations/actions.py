"""
Connector actions: steps that use a workspace's own app connections.

Each action names its connection in the `connection` input. The engine
decrypts that workspace's credentials just before the step runs and
passes them in ctx.credentials; actions never see other workspaces'
credentials and never store them.
"""

import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote, urljoin

import requests

from autoflow.engine.actions import Action, ActionError, InputSpec, register
from autoflow.security.net import UnsafeURL, check_public_url


RESPONSE_LIMIT = 100_000


def _http_error(response, app):
    retryable = response.status_code == 429 or response.status_code >= 500
    if response.status_code == 401:
        return ActionError(f"{app} rejected the credentials (401). Reconnect the app.", retryable=False)
    return ActionError(
        f"{app} returned {response.status_code}: {response.text[:300]}", retryable=retryable
    )


# --- Airtable ---------------------------------------------------------------

def _airtable_upsert(ctx, inputs):
    config, secrets = ctx.credentials["config"], ctx.credentials["secrets"]
    url = f"https://api.airtable.com/v0/{config['base_id']}/{quote(inputs['table'], safe='')}"
    headers = {"Authorization": f"Bearer {secrets['token']}", "Content-Type": "application/json"}
    match_field = inputs.get("match_field") or "Email"
    fields = inputs["fields"]

    if not isinstance(fields, dict) or match_field not in fields:
        raise ActionError(f"fields must be an object that includes {match_field}.", retryable=False)

    value = str(fields[match_field]).replace("\\", "\\\\").replace("'", "\\'")
    response = requests.get(
        url,
        headers=headers,
        params={"filterByFormula": f"{{{match_field}}} = '{value}'", "maxRecords": 1},
        timeout=20,
    )
    if not response.ok:
        raise _http_error(response, "Airtable")

    records = response.json().get("records", [])

    if records:
        record = records[0]
        if all(record.get("fields", {}).get(k) == v for k, v in fields.items()):
            return {"record_id": record["id"], "operation": "unchanged"}

        response = requests.patch(
            f"{url}/{record['id']}", headers=headers, json={"fields": fields, "typecast": True}, timeout=20
        )
        operation = "updated"
    else:
        response = requests.post(url, headers=headers, json={"fields": fields, "typecast": True}, timeout=20)
        operation = "created"

    if not response.ok:
        raise _http_error(response, "Airtable")

    return {"record_id": response.json()["id"], "operation": operation}


register(Action(
    name="airtable_upsert",
    description="Create or update an Airtable record, matched on one field (e.g. Email).",
    handler=_airtable_upsert,
    inputs={
        "connection": InputSpec("string", description="Name of an airtable connection"),
        "table": InputSpec("string"),
        "fields": InputSpec("any", description="Object of field name -> value"),
        "match_field": InputSpec("string", required=False, description="Default: Email"),
    },
    outputs={"record_id": "text", "operation": "created | updated | unchanged"},
    side_effect=True,
    idempotent=True,
    uses_network=True,
    connection_provider="airtable",
    simulate=lambda ctx, inputs: {"record_id": None, "operation": "simulated", "dry_run": True},
))


# --- Email over SMTP --------------------------------------------------------

def _smtp_send(ctx, inputs):
    # Global safety switch, same as the original email sender
    if os.getenv("EMAIL_SEND_ENABLED", "false").lower() != "true":
        raise ActionError("Email sending is disabled on this server (EMAIL_SEND_ENABLED).", retryable=False)

    config, secrets = ctx.credentials["config"], ctx.credentials["secrets"]
    recipient = inputs["to"]
    subject = inputs["subject"]

    # Optional per-connection redirect for testing
    if config.get("test_recipient"):
        subject = f"[TEST for {recipient}] {subject}"
        recipient = config["test_recipient"]

    message = EmailMessage()
    message["From"] = config["from_address"]
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(inputs["body"])

    try:
        with smtplib.SMTP_SSL(
            config["host"], int(config.get("port") or 465), context=ssl.create_default_context(), timeout=20
        ) as server:
            server.login(config["username"], secrets["password"])
            server.send_message(message)
    except smtplib.SMTPAuthenticationError as error:
        raise ActionError("The mail server rejected the login. Reconnect the account.", retryable=False) from error
    except (smtplib.SMTPException, OSError) as error:
        raise ActionError(f"Could not send email: {error}") from error

    return {"sent": True, "to": inputs["to"], "delivered_to": recipient}


register(Action(
    name="smtp_send_email",
    description="Send an email from the workspace's own mailbox (SMTP connection).",
    handler=_smtp_send,
    inputs={
        "connection": InputSpec("string", description="Name of an smtp connection"),
        "to": InputSpec("string"),
        "subject": InputSpec("string"),
        "body": InputSpec("string"),
    },
    outputs={"sent": "boolean", "to": "email", "delivered_to": "email"},
    side_effect=True,
    idempotent=False,
    requires_approval=True,
    uses_network=True,
    connection_provider="smtp",
    simulate=lambda ctx, inputs: {"sent": False, "to": inputs["to"], "dry_run": True},
))


# --- Generic REST API -------------------------------------------------------

def _http(ctx, inputs, method):
    url = inputs["url"]
    headers = dict(inputs.get("headers") or {})

    if ctx.credentials:
        config, secrets = ctx.credentials["config"], ctx.credentials["secrets"]
        if config.get("base_url") and not url.startswith(("http://", "https://")):
            url = urljoin(config["base_url"].rstrip("/") + "/", url.lstrip("/"))
        headers[config["header_name"]] = secrets["header_value"]

    try:
        check_public_url(url)
    except UnsafeURL as error:
        raise ActionError(str(error), retryable=False) from error

    body = inputs.get("body")
    response = requests.request(
        method,
        url,
        headers=headers,
        json=body if isinstance(body, (dict, list)) else None,
        data=body if isinstance(body, str) else None,
        timeout=30,
        allow_redirects=False,
    )

    if response.status_code >= 400:
        raise _http_error(response, "The API")

    try:
        parsed = response.json()
    except ValueError:
        parsed = response.text[:RESPONSE_LIMIT]

    return {"status": response.status_code, "body": parsed}


HTTP_INPUTS = {
    "url": InputSpec("string", description="Full URL, or a path when the connection has a base_url"),
    "connection": InputSpec("string", required=False, description="Name of an http connection"),
    "headers": InputSpec("any", required=False),
}

register(Action(
    name="http_get",
    description="Read data from any public REST API.",
    handler=lambda ctx, inputs: _http(ctx, inputs, "GET"),
    inputs=HTTP_INPUTS,
    outputs={"status": "number", "body": "JSON or text"},
    uses_network=True,
    connection_provider="http",
))

register(Action(
    name="http_send",
    description="Send data to any public REST API (POST, PUT, PATCH or DELETE).",
    handler=lambda ctx, inputs: _http(ctx, inputs, inputs.get("method") or "POST"),
    inputs={
        **HTTP_INPUTS,
        "method": InputSpec("string", required=False, description="POST (default), PUT, PATCH or DELETE"),
        "body": InputSpec("any", required=False),
    },
    outputs={"status": "number", "body": "JSON or text"},
    side_effect=True,
    idempotent=False,
    uses_network=True,
    connection_provider="http",
    simulate=lambda ctx, inputs: {"status": None, "body": None, "dry_run": True},
))


# --- Google Sheets ----------------------------------------------------------

def _sheets_append(ctx, inputs):
    values = inputs["values"]
    if not isinstance(values, list):
        raise ActionError("values must be a list (one row).", retryable=False)

    sheet_range = quote(f"{inputs.get('sheet_name') or 'Sheet1'}!A1", safe="")
    response = requests.post(
        f"https://sheets.googleapis.com/v4/spreadsheets/{quote(inputs['spreadsheet_id'], safe='')}"
        f"/values/{sheet_range}:append",
        params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
        headers={"Authorization": f"Bearer {ctx.credentials['secrets']['access_token']}"},
        json={"values": [values]},
        timeout=20,
    )

    if not response.ok:
        raise _http_error(response, "Google Sheets")

    return {"updated_range": response.json().get("updates", {}).get("updatedRange")}


register(Action(
    name="google_sheets_append_row",
    description="Add a row to a Google Sheet.",
    handler=_sheets_append,
    inputs={
        "connection": InputSpec("string", description="Name of a google connection"),
        "spreadsheet_id": InputSpec("string"),
        "values": InputSpec("any", description="List of cell values for one row"),
        "sheet_name": InputSpec("string", required=False, description="Default: Sheet1"),
    },
    outputs={"updated_range": "text"},
    side_effect=True,
    idempotent=False,
    uses_network=True,
    connection_provider="google",
    simulate=lambda ctx, inputs: {"updated_range": None, "dry_run": True},
))
