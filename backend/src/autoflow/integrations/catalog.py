"""
The apps a workspace can connect, and what each connection needs.

`secret_fields` are encrypted at rest and never returned by the API;
`config_fields` are ordinary settings.
"""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Provider:
    name: str
    label: str
    auth: str  # api_key | password | oauth2
    secret_fields: tuple[str, ...] = ()
    config_fields: tuple[str, ...] = ()
    required_config: tuple[str, ...] = ()
    oauth: dict = field(default_factory=dict)


PROVIDERS = {
    provider.name: provider
    for provider in (
        Provider(
            name="airtable",
            label="Airtable",
            auth="api_key",
            secret_fields=("token",),
            config_fields=("base_id",),
            required_config=("base_id",),
        ),
        Provider(
            name="smtp",
            label="Email (SMTP, e.g. Gmail app password)",
            auth="password",
            secret_fields=("password",),
            config_fields=("host", "port", "username", "from_address", "test_recipient"),
            required_config=("host", "username", "from_address"),
        ),
        Provider(
            name="shopify",
            label="Shopify store (Admin API access token)",
            auth="api_key",
            secret_fields=("access_token",),
            config_fields=("shop_domain",),
            required_config=("shop_domain",),
        ),
        Provider(
            name="imap",
            label="Incoming email (IMAP, e.g. Gmail app password)",
            auth="password",
            secret_fields=("password",),
            config_fields=("host", "port", "username"),
            required_config=("host", "username"),
        ),
        Provider(
            name="http",
            label="Any REST API (API key header)",
            auth="api_key",
            secret_fields=("header_value",),
            config_fields=("header_name", "base_url"),
            required_config=("header_name",),
        ),
        Provider(
            name="google",
            label="Google (Sheets)",
            auth="oauth2",
            secret_fields=("access_token", "refresh_token", "expires_at"),
            oauth={
                "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "scopes": ["https://www.googleapis.com/auth/spreadsheets"],
                "client_id_env": "GOOGLE_CLIENT_ID",
                "client_secret_env": "GOOGLE_CLIENT_SECRET",
                # Ask Google for a refresh token
                "extra_params": {"access_type": "offline", "prompt": "consent"},
            },
        ),
    )
}


def oauth_client(provider):
    """Return (client_id, client_secret) for an OAuth provider, or None."""

    client_id = os.getenv(provider.oauth["client_id_env"], "")
    client_secret = os.getenv(provider.oauth["client_secret_env"], "")

    if not client_id or not client_secret:
        return None

    return client_id, client_secret


def describe():
    return [
        {
            "name": p.name,
            "label": p.label,
            "auth": p.auth,
            "secret_fields": list(p.secret_fields),
            "config_fields": list(p.config_fields),
            "required_config": list(p.required_config),
            "available": p.auth != "oauth2" or oauth_client(p) is not None,
        }
        for p in PROVIDERS.values()
    ]
