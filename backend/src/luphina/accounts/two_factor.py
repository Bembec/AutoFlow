"""
Two-factor login with an authenticator app (TOTP, RFC 6238) and
one-time recovery codes.

- The shared secret is stored encrypted (luphina.security.vault).
- A code is accepted for the current 30-second step and one step either
  side (clock drift), and never twice (the last used step is stored).
- Recovery codes are shown once; only their SHA-256 hashes are kept, and
  each works a single time.
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

from luphina.accounts.security import verify_password
from luphina.security import vault


STEP_SECONDS = 30
DIGITS = 6
RECOVERY_CODE_COUNT = 10
ISSUER = "Luphina"


class TwoFactorError(Exception):
    """A two-factor request that cannot be completed."""


def new_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _key(secret):
    padding = "=" * (-len(secret) % 8)
    return base64.b32decode(secret.upper() + padding)


def code_at(secret, step):
    digest = hmac.new(_key(secret), struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(number % 10**DIGITS).zfill(DIGITS)


def current_step(now=None):
    return int((now if now is not None else time.time()) // STEP_SECONDS)


def matching_step(secret, code, last_step=None, now=None):
    """The step the code belongs to (within ±1 step and not reused), or None."""

    code = "".join(ch for ch in str(code) if ch.isdigit())
    if len(code) != DIGITS:
        return None

    step = current_step(now)
    for candidate in (step - 1, step, step + 1):
        if last_step is not None and candidate <= last_step:
            continue
        if hmac.compare_digest(code_at(secret, candidate), code):
            return candidate
    return None


def provisioning_uri(secret, account):
    # Literal ":" between issuer and account works in every authenticator app
    label = f"{quote(ISSUER)}:{quote(account)}"
    return f"otpauth://totp/{label}?secret={secret}&issuer={ISSUER}&digits={DIGITS}&period={STEP_SECONDS}"


def _hash_recovery(code):
    return hashlib.sha256(code.replace("-", "").lower().encode()).hexdigest()


def _new_recovery_codes():
    codes = [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(RECOVERY_CODE_COUNT)]
    return codes, [_hash_recovery(code) for code in codes]


# --- account operations -------------------------------------------------------

def start_setup(session, user):
    """Create a new (not yet active) secret; returns (secret, otpauth URI)."""

    if user.totp_enabled:
        raise TwoFactorError("Two-factor login is already on. Turn it off first to set up a new device.")

    secret = new_secret()
    user.totp_secret_encrypted = vault.encrypt_json({"secret": secret})
    user.totp_last_step = None
    session.flush()
    return secret, provisioning_uri(secret, user.email)


def enable(session, user, code):
    """Confirm the authenticator works; returns the one-time recovery codes."""

    if user.totp_enabled:
        raise TwoFactorError("Two-factor login is already on.")
    if not user.totp_secret_encrypted:
        raise TwoFactorError("Start the setup first.")

    secret = vault.decrypt_json(user.totp_secret_encrypted)["secret"]
    step = matching_step(secret, code)
    if step is None:
        raise TwoFactorError("That code is not right. Check the time on your phone and try the newest code.")

    codes, hashes = _new_recovery_codes()
    user.totp_enabled = True
    user.totp_last_step = step
    user.recovery_codes = hashes
    session.flush()
    return codes


def check_code(session, user, code):
    """True if the code is a fresh authenticator code or an unused recovery code."""

    if not user.totp_enabled or not code:
        return False

    secret = vault.decrypt_json(user.totp_secret_encrypted)["secret"]
    step = matching_step(secret, code, user.totp_last_step)
    if step is not None:
        user.totp_last_step = step
        session.flush()
        return True

    hashed = _hash_recovery(str(code))
    remaining = list(user.recovery_codes or [])
    if hashed in remaining:
        remaining.remove(hashed)
        user.recovery_codes = remaining  # each recovery code works once
        session.flush()
        return True

    return False


def disable(session, user, password, code):
    if not user.totp_enabled:
        raise TwoFactorError("Two-factor login is not on.")
    if not verify_password(password, user.password_hash):
        raise TwoFactorError("Incorrect password.")
    if not check_code(session, user, code):
        raise TwoFactorError("That code is not right.")

    user.totp_enabled = False
    user.totp_secret_encrypted = None
    user.totp_last_step = None
    user.recovery_codes = None
    session.flush()


def recovery_codes_left(user):
    return len(user.recovery_codes or []) if user.totp_enabled else 0
