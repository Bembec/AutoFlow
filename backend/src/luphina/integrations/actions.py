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

from luphina import config as app_config
from luphina.engine.actions import Action, ActionError, InputSpec, register
from luphina.security.net import UnsafeURL, check_public_url


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
    # Lets recipients and mail providers report abuse to us, traced to the workspace
    message["X-Luphina-Workspace"] = str(ctx.workspace_id)
    message["X-Report-Abuse"] = f"{app_config.PUBLIC_URL}/report-abuse?workspace={ctx.workspace_id}"
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


# --- Shopify Admin API ------------------------------------------------------

def _shopify_order_url(ctx, order_id):
    from luphina.integrations.connections import SHOPIFY_DOMAIN

    domain = str(ctx.credentials["config"]["shop_domain"]).lower()
    if not SHOPIFY_DOMAIN.fullmatch(domain):
        raise ActionError("The Shopify connection has an invalid shop_domain.", retryable=False)

    version = os.getenv("SHOPIFY_API_VERSION", "2025-07")
    order_id = str(order_id).strip()
    if not order_id.isdigit():
        raise ActionError("order_id must be the numeric Shopify order id.", retryable=False)

    headers = {
        "X-Shopify-Access-Token": ctx.credentials["secrets"]["access_token"],
        "Content-Type": "application/json",
    }
    return f"https://{domain}/admin/api/{version}/orders/{order_id}.json", headers, order_id


def _shopify_tag_order(ctx, inputs):
    url, headers, order_id = _shopify_order_url(ctx, inputs["order_id"])

    response = requests.get(url, headers=headers, params={"fields": "id,tags"}, timeout=20)
    if not response.ok:
        raise _http_error(response, "Shopify")

    existing = [t.strip() for t in (response.json().get("order", {}).get("tags") or "").split(",") if t.strip()]
    wanted = [t.strip() for t in str(inputs["tags"]).split(",") if t.strip()]
    merged = existing + [t for t in wanted if t not in existing]

    if merged == existing:
        return {"tags": ", ".join(merged), "changed": False}

    response = requests.put(
        url, headers=headers, json={"order": {"id": int(order_id), "tags": ", ".join(merged)}}, timeout=20
    )
    if not response.ok:
        raise _http_error(response, "Shopify")

    return {"tags": ", ".join(merged), "changed": True}


register(Action(
    name="shopify_tag_order",
    description="Add tags to a Shopify order (e.g. \"invoiced\"). Existing tags are kept.",
    handler=_shopify_tag_order,
    inputs={
        "connection": InputSpec("string", description="Name of a shopify connection"),
        "order_id": InputSpec("any", description="Numeric Shopify order id, e.g. {{trigger.id}}"),
        "tags": InputSpec("string", description="Comma-separated tags"),
    },
    outputs={"tags": "all tags on the order", "changed": "boolean"},
    side_effect=True,
    idempotent=True,
    uses_network=True,
    connection_provider="shopify",
    simulate=lambda ctx, inputs: {"tags": inputs["tags"], "changed": False, "dry_run": True},
))


def _shopify_note_order(ctx, inputs):
    url, headers, order_id = _shopify_order_url(ctx, inputs["order_id"])

    response = requests.put(
        url, headers=headers, json={"order": {"id": int(order_id), "note": str(inputs["note"])}}, timeout=20
    )
    if not response.ok:
        raise _http_error(response, "Shopify")

    return {"note": str(inputs["note"])}


register(Action(
    name="shopify_set_order_note",
    description="Set the internal note on a Shopify order (replaces the current note).",
    handler=_shopify_note_order,
    inputs={
        "connection": InputSpec("string", description="Name of a shopify connection"),
        "order_id": InputSpec("any", description="Numeric Shopify order id, e.g. {{trigger.id}}"),
        "note": InputSpec("string"),
    },
    outputs={"note": "text"},
    side_effect=True,
    idempotent=True,
    uses_network=True,
    connection_provider="shopify",
    simulate=lambda ctx, inputs: {"note": inputs["note"], "dry_run": True},
))


# --- WooCommerce REST API ---------------------------------------------------

WOOCOMMERCE_STATUSES = ("pending", "processing", "on-hold", "completed", "cancelled")


def _woocommerce_order_url(ctx, order_id, suffix=""):
    store = str(ctx.credentials["config"]["store_url"]).rstrip("/")
    order_id = str(order_id).strip()

    if not order_id.isdigit():
        raise ActionError("order_id must be the numeric WooCommerce order id.", retryable=False)
    if not store.startswith("https://"):
        raise ActionError("The WooCommerce connection must use https.", retryable=False)

    url = f"{store}/wp-json/wc/v3/orders/{order_id}{suffix}"
    try:
        check_public_url(url)
    except UnsafeURL as error:
        raise ActionError(str(error), retryable=False) from error

    secrets = ctx.credentials["secrets"]
    return url, (secrets["consumer_key"], secrets["consumer_secret"])


def _woocommerce_note(ctx, inputs):
    url, auth = _woocommerce_order_url(ctx, inputs["order_id"], "/notes")
    response = requests.post(
        url,
        auth=auth,
        json={"note": str(inputs["note"]), "customer_note": bool(inputs.get("customer_note"))},
        timeout=20,
        allow_redirects=False,
    )
    if not response.ok:
        raise _http_error(response, "WooCommerce")
    return {"note_id": response.json().get("id")}


register(Action(
    name="woocommerce_add_order_note",
    description="Add a note to a WooCommerce order (private, or visible to the customer).",
    handler=_woocommerce_note,
    inputs={
        "connection": InputSpec("string", description="Name of a woocommerce connection"),
        "order_id": InputSpec("any", description="Numeric order id, e.g. {{trigger.id}}"),
        "note": InputSpec("string"),
        "customer_note": InputSpec("boolean", required=False, description="true = the customer sees it"),
    },
    outputs={"note_id": "number"},
    side_effect=True,
    idempotent=False,
    uses_network=True,
    connection_provider="woocommerce",
    simulate=lambda ctx, inputs: {"note_id": None, "dry_run": True},
))


def _woocommerce_status(ctx, inputs):
    status = str(inputs["status"]).strip().lower()
    if status not in WOOCOMMERCE_STATUSES:
        raise ActionError(f"status must be one of: {', '.join(WOOCOMMERCE_STATUSES)}", retryable=False)

    url, auth = _woocommerce_order_url(ctx, inputs["order_id"])
    response = requests.put(url, auth=auth, json={"status": status}, timeout=20, allow_redirects=False)
    if not response.ok:
        raise _http_error(response, "WooCommerce")
    return {"status": response.json().get("status", status)}


register(Action(
    name="woocommerce_set_order_status",
    description="Change a WooCommerce order's status (the store may email the customer, so it needs approval).",
    handler=_woocommerce_status,
    inputs={
        "connection": InputSpec("string", description="Name of a woocommerce connection"),
        "order_id": InputSpec("any", description="Numeric order id, e.g. {{trigger.id}}"),
        "status": InputSpec("string", description="pending, processing, on-hold, completed or cancelled"),
    },
    outputs={"status": "text"},
    side_effect=True,
    idempotent=True,
    requires_approval=True,
    uses_network=True,
    connection_provider="woocommerce",
    simulate=lambda ctx, inputs: {"status": inputs["status"], "dry_run": True},
))


# --- MCP servers (V39) -------------------------------------------------------

MCP_INPUTS = {
    "connection": InputSpec("string", description="Name of an MCP server connection"),
    "tool": InputSpec("string", description="Tool name, as listed on the connection"),
    "arguments": InputSpec("any", required=False, description='The tool\'s inputs, e.g. {"query": "{{trigger.text}}"}'),
}
MCP_OUTPUTS = {"text": "the tool's text answer", "data": "structured result, if the tool gives one", "tool": "text"}


def _mcp(ctx, inputs, read_only):
    from luphina.integrations import mcp

    try:
        return mcp.call(ctx.credentials["config"], ctx.credentials["secrets"], inputs["tool"],
                        inputs.get("arguments"), read_only=read_only)
    except mcp.MCPError as error:
        raise ActionError(str(error), retryable=error.retryable) from error


register(Action(
    name="mcp_read",
    description="Look something up with a read-only tool from an MCP server (search, fetch, get).",
    handler=lambda ctx, inputs: _mcp(ctx, inputs, read_only=True),
    inputs=MCP_INPUTS,
    outputs=MCP_OUTPUTS,
    uses_network=True,
    connection_provider="mcp",
))

register(Action(
    name="mcp_call_tool",
    description="Use a tool from an MCP server that may change something. Always waits for approval.",
    handler=lambda ctx, inputs: _mcp(ctx, inputs, read_only=False),
    inputs=MCP_INPUTS,
    outputs=MCP_OUTPUTS,
    side_effect=True,
    idempotent=False,
    requires_approval=True,
    uses_network=True,
    connection_provider="mcp",
    simulate=lambda ctx, inputs: {"tool": inputs.get("tool"), "text": "", "data": None, "dry_run": True},
))

