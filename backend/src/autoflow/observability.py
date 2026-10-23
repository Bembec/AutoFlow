"""
Optional error tracking with Sentry.

Set SENTRY_DSN (and `pip install sentry-sdk`) to report unhandled errors
from the API and the worker. No personal data is sent (send_default_pii
is off) and performance tracing is off unless SENTRY_TRACES_SAMPLE_RATE
is set.
"""

import logging
import os

from autoflow import __version__, config


logger = logging.getLogger("autoflow")


def init_error_tracking(component):
    """Start Sentry if configured. Returns True when it is active."""

    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return False

    try:
        import sentry_sdk
    except ImportError:
        logger.warning("SENTRY_DSN is set but sentry-sdk is not installed; error tracking is off.")
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=config.ENVIRONMENT,
        release=f"autoflow@{__version__}",
        send_default_pii=False,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0")),
    )
    sentry_sdk.set_tag("component", component)
    return True
