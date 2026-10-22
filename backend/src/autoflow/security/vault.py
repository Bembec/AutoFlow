"""
Encryption for stored secrets (integration credentials, webhook secrets).

Secrets are encrypted with Fernet (AES-128-CBC + HMAC-SHA256).

Key management:
- Production: set AUTOFLOW_SECRET_KEYS to one or more comma-separated
  Fernet keys. The first key encrypts; all keys decrypt, so keys can be
  rotated by putting a new key first (later: a cloud KMS or Vault).
- Development: if the variable is missing, a key is generated once and
  kept in data/output/secret.key (git-ignored).
"""

import json
import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from autoflow import config


class VaultError(Exception):
    """A secret could not be decrypted (wrong or rotated-out key)."""


def generate_key():
    return Fernet.generate_key().decode()


def _development_key():
    key_path = config.OUTPUT_DIR / "secret.key"

    if not key_path.exists():
        key_path.write_text(generate_key(), encoding="utf-8")

    return key_path.read_text(encoding="utf-8").strip()


@lru_cache(maxsize=1)
def _fernet():
    keys = os.getenv("AUTOFLOW_SECRET_KEYS", "").strip() or _development_key()
    return MultiFernet([Fernet(key.strip().encode()) for key in keys.split(",") if key.strip()])


def encrypt_json(data):
    return _fernet().encrypt(json.dumps(data).encode()).decode()


def decrypt_json(token, ttl=None):
    """Decrypt; with `ttl` (seconds) older tokens are rejected."""

    try:
        return json.loads(_fernet().decrypt(token.encode(), ttl=ttl))
    except InvalidToken as error:
        raise VaultError("Secret is invalid, expired or encrypted with an unknown key.") from error


def rotate(token):
    """Re-encrypt a secret with the current primary key."""
    return _fernet().rotate(token.encode()).decode()


def mask(value):
    """Show only enough of a secret to recognise it."""

    value = str(value or "")
    if len(value) <= 8:
        return "•" * len(value)
    return f"{value[:3]}…{value[-4:]}"
