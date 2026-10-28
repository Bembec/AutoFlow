"""Appends timestamped events to Luphina's activity log."""

from datetime import datetime

from luphina import config


def timestamp_now():
    """Return the current local time as an ISO-8601 string."""

    return datetime.now().astimezone().isoformat(timespec="seconds")


def write_log_lines(lines):
    """Append already-formatted lines to the activity log."""

    with config.ACTIVITY_LOG_PATH.open("a", encoding="utf-8") as log:
        for line in lines:
            log.write(f"{line}\n")
