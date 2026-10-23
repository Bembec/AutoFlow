"""
Connection health: check that stored credentials still work.

A check makes the smallest read-only call each app offers (logging in,
or fetching the account) and never sends or changes anything. A failed
check marks the connection as needing reconnection and tells the owner,
before a live run trips over it.
"""

import imaplib
import os
import smtplib
import ssl

import requests

from autoflow import notifications
from autoflow.integrations import connections
from autoflow.security import vault
from autoflow.security.net import UnsafeURL, check_public_url
from autoflow.storage.db import utc_now


class CheckFailed(Exception):
    pass


def _http_ok(response, what):
    if response.status_code in (401, 403):
        raise CheckFailed(f"{what} rejected the credentials ({response.status_code}).")
    if response.status_code >= 400:
        raise CheckFailed(f"{what} answered with an error ({response.status_code}).")


def _smtp(config, secrets):
    with smtplib.SMTP_SSL(config["host"], int(config.get("port") or 465),
                          context=ssl.create_default_context(), timeout=20) as server:
        server.login(config["username"], secrets["password"])


def _imap(config, secrets):
    client = imaplib.IMAP4_SSL(config["host"], int(config.get("port") or 993), timeout=20)
    try:
        client.login(config["username"], secrets["password"])
    finally:
        try:
            client.logout()
        except Exception:  # noqa: BLE001 - logging out is best effort
            pass


def _airtable(config, secrets):
    response = requests.get("https://api.airtable.com/v0/meta/whoami",
                            headers={"Authorization": f"Bearer {secrets['token']}"}, timeout=20)
    _http_ok(response, "Airtable")


def _shopify(config, secrets):
    domain = str(config["shop_domain"]).lower()
    if not connections.SHOPIFY_DOMAIN.fullmatch(domain):
        raise CheckFailed("The shop_domain is not a valid myshopify.com address.")
    version = os.getenv("SHOPIFY_API_VERSION", "2025-07")
    response = requests.get(f"https://{domain}/admin/api/{version}/shop.json",
                            headers={"X-Shopify-Access-Token": secrets["access_token"]}, timeout=20)
    _http_ok(response, "Shopify")


def _woocommerce(config, secrets):
    url = f"{str(config['store_url']).rstrip('/')}/wp-json/wc/v3/orders?per_page=1"
    try:
        check_public_url(url)
    except UnsafeURL as error:
        raise CheckFailed(str(error)) from error
    response = requests.get(url, auth=(secrets["consumer_key"], secrets["consumer_secret"]), timeout=20)
    _http_ok(response, "WooCommerce")


CHECKS = {
    "smtp": _smtp,
    "imap": _imap,
    "airtable": _airtable,
    "shopify": _shopify,
    "woocommerce": _woocommerce,
}
# Can't be checked without side effects (posting a message) or a known endpoint
UNCHECKABLE = {
    "slack": "Slack webhooks can only be tested by posting a message, so they are checked when used.",
    "http": "Custom APIs have no standard test call, so they are checked when used.",
}


def check(session, connection):
    """Run the check. Returns {"ok": True|False|None, "message": str}."""

    connection.last_checked_at = utc_now()

    if connection.provider in UNCHECKABLE:
        session.commit()
        return {"ok": None, "message": UNCHECKABLE[connection.provider]}

    try:
        if connection.provider == "google":
            # Asking Google for a fresh access token proves the refresh token works
            secrets = vault.decrypt_json(connection.encrypted_secrets)
            connections._refresh(session, connection, connections.PROVIDERS["google"], secrets)
        else:
            secrets = vault.decrypt_json(connection.encrypted_secrets)
            CHECKS[connection.provider](dict(connection.config), secrets)
    except connections.ReconnectNeeded as failure:
        return _failed(session, connection, str(failure))
    except CheckFailed as failure:
        return _failed(session, connection, str(failure))
    except (smtplib.SMTPAuthenticationError, imaplib.IMAP4.error):
        return _failed(session, connection, "The mail server rejected the login.")
    except (OSError, smtplib.SMTPException, requests.RequestException) as failure:
        # Network trouble is not proof the credentials are bad: report, don't mark broken
        session.commit()
        return {"ok": False, "message": f"Could not reach the service: {failure}"}

    connection.status = "active"
    connection.last_error = None
    session.commit()
    return {"ok": True, "message": "Connected and working."}


def _failed(session, connection, message):
    was_active = connection.status != "error"
    connection.status = "error"
    connection.last_error = message
    if was_active:
        notify_broken(session, connection)
    session.commit()
    return {"ok": False, "message": message}


def notify_broken(session, connection):
    """Tell the owner a connection needs reconnecting (not committed here)."""
    notifications.enqueue(
        session, connection.workspace_id, "failure",
        f"Reconnect “{connection.name}”",
        f"The {connection.provider} connection “{connection.name}” stopped working: {connection.last_error} "
        "Workflows that use it will fail until it is reconnected.",
        link="/connections",
    )
