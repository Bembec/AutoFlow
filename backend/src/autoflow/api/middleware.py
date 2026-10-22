"""
HTTP middleware: request IDs and access logs, security headers, and a
rate limit on sign-in endpoints against password guessing.
"""

import logging
import secrets
import threading
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

from autoflow import config


logger = logging.getLogger("autoflow.http")

# Sign-in attempts allowed per client IP per window
AUTH_LIMIT = 10
AUTH_WINDOW_SECONDS = 60
AUTH_PATHS = ("/auth/login", "/auth/register")


class RateLimiter:
    """Sliding-window counter kept in memory.

    Per process: with several API processes, put a shared limiter (e.g.
    Redis or the load balancer) in front for a strict global limit.
    """

    def __init__(self, limit, window_seconds):
        self.limit = limit
        self.window = window_seconds
        self.hits = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, key, now=None):
        now = now or time.monotonic()
        with self.lock:
            hits = self.hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True


auth_limiter = RateLimiter(AUTH_LIMIT, AUTH_WINDOW_SECONDS)


def client_ip(request):
    # Behind a proxy, run uvicorn with --proxy-headers so this is the real client
    return request.client.host if request.client else "unknown"


async def http_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or secrets.token_hex(8)
    started = time.perf_counter()

    if request.url.path in AUTH_PATHS and request.method == "POST":
        if not auth_limiter.allow(client_ip(request)):
            return JSONResponse(
                {"detail": "Too many sign-in attempts. Please wait a minute and try again."},
                status_code=429,
                headers={"Retry-After": str(AUTH_WINDOW_SECONDS), "X-Request-ID": request_id},
            )

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if config.ENVIRONMENT != "development":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    logger.info(
        "%s %s %s %.0fms request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - started) * 1000,
        request_id,
    )
    return response
