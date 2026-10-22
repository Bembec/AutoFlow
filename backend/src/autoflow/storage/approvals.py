"""
Stores human-approval requests in SQLite.

An approval is created when AutoFlow needs a human decision (an AI
classification or an outgoing email) and nobody is at the terminal.
At most one *pending* approval exists per kind and customer email.
"""

import json
import sqlite3

from autoflow.activity_log import timestamp_now
from autoflow.storage.database import database_path


APPROVAL_KINDS = ("classification", "email")


def initialize_approvals_table():
    """Create the approvals table and its pending-uniqueness index."""

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                customer_email TEXT NOT NULL,
                payload TEXT NOT NULL,
                decision TEXT,
                created_at TEXT NOT NULL,
                decided_at TEXT
            )
            """
        )

        # Re-running the workflow refreshes a pending request
        # instead of creating a duplicate
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS one_pending_approval
            ON approvals (kind, customer_email)
            WHERE status = 'pending'
            """
        )


def _row_to_approval(row):
    approval = dict(row)
    approval["payload"] = json.loads(approval["payload"])
    approval["decision"] = (
        json.loads(approval["decision"]) if approval["decision"] else None
    )
    return approval


def upsert_pending_approval(kind, customer_email, payload):
    """Create a pending approval, or refresh the existing pending one."""

    if kind not in APPROVAL_KINDS:
        raise ValueError(f"Unknown approval kind: {kind}")

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO approvals (kind, customer_email, payload, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (kind, customer_email) WHERE status = 'pending'
            DO UPDATE SET
                payload = excluded.payload,
                created_at = excluded.created_at
            """,
            (kind, customer_email, json.dumps(payload), timestamp_now()),
        )


def list_approvals(status=None, kind=None):
    """Return approvals, newest first, optionally filtered."""

    query = "SELECT * FROM approvals WHERE 1 = 1"
    parameters = []

    if status is not None:
        query += " AND status = ?"
        parameters.append(status)

    if kind is not None:
        query += " AND kind = ?"
        parameters.append(kind)

    query += " ORDER BY id DESC"

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, parameters).fetchall()

    return [_row_to_approval(row) for row in rows]


def get_approval(approval_id):
    """Return one approval, or None."""

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT * FROM approvals WHERE id = ?", (approval_id,)
        ).fetchone()

    return _row_to_approval(row) if row is not None else None


def claim_pending_approval(approval_id, status, decision):
    """Atomically move a pending approval to a final status.

    Returns True only for the caller that made the change, so the same
    approval can never be acted on twice.
    """

    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(
            """
            UPDATE approvals
            SET status = ?, decision = ?, decided_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            (status, json.dumps(decision), timestamp_now(), approval_id),
        )

    return cursor.rowcount == 1


def set_approval_status(approval_id, status):
    """Record the final outcome after an approved action ran."""

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE approvals SET status = ? WHERE id = ?",
            (status, approval_id),
        )
