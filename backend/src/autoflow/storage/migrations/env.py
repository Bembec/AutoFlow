"""Alembic environment: applies AutoFlow's schema migrations."""

from alembic import context

from autoflow.storage import models  # noqa: F401  (registers every table)
from autoflow.storage.db import Base, engine


target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=str(engine.url),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def _sqlite_foreign_keys(connection, on):
    """Turn SQLite's foreign-key enforcement on or off for this connection.

    Batch migrations alter a SQLite table by copying it and dropping the
    old one. With foreign keys on, that DROP deletes every row that points
    at the table through ON DELETE CASCADE (memberships, workflows, runs…),
    so enforcement must be off while migrating. The PRAGMA only works
    outside a transaction, hence the raw DBAPI connection.
    """
    connection.connection.dbapi_connection.execute(f"PRAGMA foreign_keys={'ON' if on else 'OFF'}")


def run_migrations_online():
    with engine.connect() as connection:
        sqlite = connection.dialect.name == "sqlite"
        if sqlite:
            _sqlite_foreign_keys(connection, on=False)

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite needs batch mode to alter tables
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()

        if sqlite:
            # The data must still be consistent after the copy-and-rename steps
            broken = connection.connection.dbapi_connection.execute("PRAGMA foreign_key_check").fetchall()
            _sqlite_foreign_keys(connection, on=True)
            if broken:
                raise RuntimeError(f"Migration left {len(broken)} rows with broken references: {broken[:5]}")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
