"""
Password hashing and access-token helpers.

Passwords use scrypt (Python standard library) with a random salt.
Access tokens are random strings; only their SHA-256 hash is stored, so
a database leak does not reveal usable tokens.
"""

import base64
import hashlib
import hmac
import secrets


SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P
    )
    return "scrypt${}${}${}${}${}".format(
        SCRYPT_N,
        SCRYPT_R,
        SCRYPT_P,
        base64.b64encode(salt).decode(),
        base64.b64encode(digest).decode(),
    )


def verify_password(password, stored_hash):
    try:
        algorithm, n, r, p, salt, digest = stored_hash.split("$")
    except ValueError:
        return False

    if algorithm != "scrypt":
        return False

    candidate = hashlib.scrypt(
        password.encode("utf-8"),
        salt=base64.b64decode(salt),
        n=int(n),
        r=int(r),
        p=int(p),
    )
    return hmac.compare_digest(candidate, base64.b64decode(digest))


def new_access_token():
    """Return (token for the client, hash to store)."""

    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
