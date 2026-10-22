"""
Manages AutoFlow's local SQLite database.

The database stores processed customer records permanently,
preparing AutoFlow for its future API and web dashboard.
"""

import sqlite3
from datetime import datetime

from autoflow import config


# Store the database in the generated-data folder
database_path = config.DATABASE_PATH


def initialize_database():
    """Create the database tables if they do not already exist."""

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                message TEXT NOT NULL,
                category TEXT NOT NULL,
                classification_source TEXT NOT NULL,
                classification_reason TEXT NOT NULL,
                quote_eur TEXT,
                quote_usd TEXT,
                rate_date TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )

        # Store the history of every AutoFlow execution
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_timestamp TEXT NOT NULL,
                customer_count INTEGER NOT NULL,
                ai_enabled TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )

    print("AutoFlow database initialized:", database_path)


def save_customers(customers):
    """Insert new customers or update existing ones using their email."""

    updated_at = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    with sqlite3.connect(database_path) as connection:
        for customer in customers:
            connection.execute(
                """
                INSERT INTO customers (
                    customer_id,
                    name,
                    email,
                    message,
                    category,
                    classification_source,
                    classification_reason,
                    quote_eur,
                    quote_usd,
                    rate_date,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

                ON CONFLICT(email) DO UPDATE SET
                    customer_id = excluded.customer_id,
                    name = excluded.name,
                    message = excluded.message,
                    category = excluded.category,
                    classification_source =
                        excluded.classification_source,
                    classification_reason =
                        excluded.classification_reason,
                    quote_eur = excluded.quote_eur,
                    quote_usd = excluded.quote_usd,
                    rate_date = excluded.rate_date,
                    updated_at = excluded.updated_at
                """,
                (
                    customer["id"],
                    customer["name"],
                    customer["email"],
                    customer["message"],
                    customer["category"],
                    customer["classification_source"],
                    customer["classification_reason"],
                    customer["quote_eur"],
                    customer["quote_usd"],
                    customer["rate_date"],
                    updated_at,
                ),
            )

    print(f"Database synchronized: {len(customers)} customers.")


def record_workflow_run(
    customer_count,
    ai_enabled,
    status="SUCCESS",
):
    """Save a summary of one AutoFlow execution."""

    run_timestamp = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO workflow_runs (
                run_timestamp,
                customer_count,
                ai_enabled,
                status
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                run_timestamp,
                customer_count,
                ai_enabled,
                status,
            ),
        )

    print("Workflow run recorded in the database.")


def get_all_customers():
    """Return every stored customer as a list of dictionaries."""

    with sqlite3.connect(database_path) as connection:
        # Allow database rows to behave like dictionaries
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            """
            SELECT
                id,
                name,
                email,
                category,
                classification_source,
                updated_at
            FROM customers
            ORDER BY id
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_workflow_runs(limit=10):
    """Return the most recent AutoFlow execution records."""

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            """
            SELECT
                id,
                run_timestamp,
                customer_count,
                ai_enabled,
                status
            FROM workflow_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


if __name__ == "__main__":
    initialize_database()

    print("\nStored customers:")
    for customer in get_all_customers():
        print(customer)

    print("\nRecent workflow runs:")
    for workflow_run in get_workflow_runs():
        print(workflow_run)
