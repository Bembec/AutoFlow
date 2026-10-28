"""
OAuth2 "connect your app" flow.

1. start(): build the provider's consent URL. The `state` parameter is
   encrypted and expires after 10 minutes, and records which workspace
   and user started the flow, so a callback cannot be forged or replayed
   into another workspace.
2. finish(): the provider redirects back with a code; exchange it for
   access and refresh tokens and store them encrypted as a connection.
"""

import secrets as random_secrets
import time
from urllib.parse import urlencode

import requests

from luphina import config
from luphina.integrations import connections
from luphina.integrations.catalog import PROVIDERS, oauth_client
from luphina.security import vault


STATE_TTL_SECONDS = 600


class OAuthError(Exception):
    """The OAuth flow could not be completed."""


def redirect_uri(provider_name):
    return f"{config.PUBLIC_URL}/oauth/callback/{provider_name}"


def _provider(provider_name):
    provider = PROVIDERS.get(provider_name)

    if provider is None or provider.auth != "oauth2":
        raise OAuthError(f"{provider_name} does not use OAuth.")

    client = oauth_client(provider)
    if client is None:
        raise OAuthError(
            f"OAuth for {provider.label} is not configured on this server "
            f"({provider.oauth['client_id_env']} / {provider.oauth['client_secret_env']})."
        )

    return provider, client


def start(provider_name, workspace_id, user_id, connection_name):
    provider, (client_id, _) = _provider(provider_name)

    state = vault.encrypt_json({
        "provider": provider_name,
        "workspace_id": workspace_id,
        "user_id": user_id,
        "name": connection_name,
        "nonce": random_secrets.token_hex(8),
    })

    query = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri(provider_name),
        "scope": " ".join(provider.oauth["scopes"]),
        "state": state,
        **provider.oauth.get("extra_params", {}),
    }
    return f"{provider.oauth['authorize_url']}?{urlencode(query)}"


def finish(session, provider_name, code, state):
    provider, (client_id, client_secret) = _provider(provider_name)

    try:
        flow = vault.decrypt_json(state, ttl=STATE_TTL_SECONDS)
    except vault.VaultError as error:
        raise OAuthError("This sign-in link is invalid or has expired. Please start again.") from error

    if flow.get("provider") != provider_name:
        raise OAuthError("This sign-in link belongs to a different app.")

    response = requests.post(
        provider.oauth["token_url"],
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri(provider_name),
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=20,
    )

    if response.status_code >= 400:
        raise OAuthError(f"{provider.label} rejected the sign-in ({response.status_code}).")

    token = response.json()
    secrets = {
        "access_token": token["access_token"],
        "refresh_token": token.get("refresh_token", ""),
        "expires_at": time.time() + int(token.get("expires_in", 3600)),
    }

    existing = connections.get_by_name(session, flow["workspace_id"], flow["name"])
    if existing is not None and existing.provider == provider_name:
        # Reconnecting replaces the old tokens
        connections.update_secrets(session, existing, secrets)
        return existing

    return connections.create_connection(
        session,
        flow["workspace_id"],
        provider_name,
        flow["name"],
        secrets,
        {},
        user_id=flow["user_id"],
    )
