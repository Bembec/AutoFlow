"""
Workspace connections to external apps, with encrypted credentials.

Credentials are only decrypted at the moment an action needs them, and
OAuth access tokens are refreshed automatically shortly before expiry.
A revoked or failed refresh marks the connection "error" so the owner
knows to reconnect, instead of retrying forever.
"""

import re
import time

import requests
from sqlalchemy import select

from autoflow.integrations.catalog import PROVIDERS, oauth_client
from autoflow.security import vault
from autoflow.storage.db import utc_now
from autoflow.storage.models import Connection


class ConnectionError_(Exception):
    """A connection request that cannot be completed."""


class ReconnectNeeded(Exception):
    """The app no longer accepts this connection's credentials."""


REFRESH_MARGIN_SECONDS = 120
SHOPIFY_DOMAIN = re.compile(r"[a-z0-9][a-z0-9-]*\.myshopify\.com")


def _check(provider_name, secrets, config):
    provider = PROVIDERS.get(provider_name)

    if provider is None:
        raise ConnectionError_(f"Unknown provider: {provider_name}")

    unknown = set(secrets) - set(provider.secret_fields)
    if unknown:
        raise ConnectionError_(f"Unknown secret fields: {', '.join(sorted(unknown))}")

    unknown = set(config) - set(provider.config_fields)
    if unknown:
        raise ConnectionError_(f"Unknown config fields: {', '.join(sorted(unknown))}")

    missing = [name for name in provider.required_config if not config.get(name)]
    if missing:
        raise ConnectionError_(f"Missing config: {', '.join(missing)}")

    if provider_name == "shopify" and not SHOPIFY_DOMAIN.fullmatch(str(config["shop_domain"]).lower()):
        # The access token is only ever sent to the store's own Shopify address
        raise ConnectionError_("shop_domain must look like your-store.myshopify.com")

    return provider


def create_connection(session, workspace_id, provider_name, name, secrets, config, user_id=None):
    _check(provider_name, secrets, config)

    if get_by_name(session, workspace_id, name) is not None:
        raise ConnectionError_(f"A connection named {name!r} already exists.")

    connection = Connection(
        workspace_id=workspace_id,
        provider=provider_name,
        name=name,
        config=config,
        encrypted_secrets=vault.encrypt_json(secrets),
        created_by_user_id=user_id,
    )
    session.add(connection)
    session.commit()
    return connection


def list_connections(session, workspace_id):
    return session.scalars(
        select(Connection)
        .where(Connection.workspace_id == workspace_id, Connection.status != "revoked")
        .order_by(Connection.id)
    ).all()


def get_connection(session, workspace_id, connection_id):
    return session.scalar(
        select(Connection).where(
            Connection.workspace_id == workspace_id, Connection.id == connection_id
        )
    )


def get_by_name(session, workspace_id, name):
    return session.scalar(
        select(Connection).where(
            Connection.workspace_id == workspace_id,
            Connection.name == name,
            Connection.status != "revoked",
        )
    )


def update_secrets(session, connection, secrets):
    _check(connection.provider, secrets, connection.config)
    connection.encrypted_secrets = vault.encrypt_json(secrets)
    connection.status = "active"
    connection.last_error = None
    session.commit()


def revoke(session, connection):
    """Delete the stored credentials; the record stays for the audit trail."""

    connection.status = "revoked"
    connection.encrypted_secrets = vault.encrypt_json({})
    session.commit()


def masked_secrets(connection):
    try:
        secrets = vault.decrypt_json(connection.encrypted_secrets)
    except vault.VaultError:
        return {}
    return {key: vault.mask(value) for key, value in secrets.items() if key != "expires_at"}


def credentials_for(session, workspace_id, name, expected_provider):
    """Return (config, secrets) for an action, refreshing OAuth if needed."""

    connection = get_by_name(session, workspace_id, name)

    if connection is None:
        raise ReconnectNeeded(f"No connection named {name!r} in this workspace.")

    if connection.provider != expected_provider:
        raise ReconnectNeeded(
            f"Connection {name!r} is a {connection.provider} connection, "
            f"not {expected_provider}."
        )

    if connection.status == "error":
        raise ReconnectNeeded(
            f"Connection {name!r} needs reconnecting: {connection.last_error}"
        )

    secrets = vault.decrypt_json(connection.encrypted_secrets)
    provider = PROVIDERS[connection.provider]

    if provider.auth == "oauth2" and float(secrets.get("expires_at", 0)) - time.time() < REFRESH_MARGIN_SECONDS:
        secrets = _refresh(session, connection, provider, secrets)

    connection.last_used_at = utc_now()
    session.commit()
    return dict(connection.config), secrets


def _refresh(session, connection, provider, secrets):
    client = oauth_client(provider)

    if client is None or not secrets.get("refresh_token"):
        _mark_error(session, connection, "Cannot refresh: OAuth is not configured or no refresh token.")

    client_id, client_secret = client
    response = requests.post(
        provider.oauth["token_url"],
        data={
            "grant_type": "refresh_token",
            "refresh_token": secrets["refresh_token"],
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=20,
    )

    if response.status_code in (400, 401):
        # invalid_grant: the user revoked access or the token expired
        _mark_error(session, connection, f"The app rejected the refresh token ({response.status_code}).")

    response.raise_for_status()
    token = response.json()

    secrets = {
        **secrets,
        "access_token": token["access_token"],
        "expires_at": time.time() + int(token.get("expires_in", 3600)),
        # Some providers rotate the refresh token
        "refresh_token": token.get("refresh_token", secrets["refresh_token"]),
    }
    connection.encrypted_secrets = vault.encrypt_json(secrets)
    session.commit()
    return secrets


def _mark_error(session, connection, message):
    connection.status = "error"
    connection.last_error = message
    session.commit()
    raise ReconnectNeeded(f"Connection {connection.name!r} needs reconnecting: {message}")
