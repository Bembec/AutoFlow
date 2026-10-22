"""Persistence layer for AutoFlow."""

from pathlib import Path


MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def alembic_config():
    """Return an Alembic configuration pointing at AutoFlow's migrations."""

    from alembic.config import Config

    configuration = Config()
    configuration.set_main_option("script_location", str(MIGRATIONS_DIR))
    return configuration


def initialize_storage():
    """Bring the database schema up to the latest migration."""

    from alembic import command

    command.upgrade(alembic_config(), "head")


def database_status():
    """Report whether the database is reachable and fully migrated."""

    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory
    from sqlalchemy.exc import SQLAlchemyError

    from autoflow.storage.db import engine

    head = ScriptDirectory.from_config(alembic_config()).get_current_head()

    try:
        with engine.connect() as connection:
            current = MigrationContext.configure(connection).get_current_revision()
    except SQLAlchemyError as error:
        return {"database": "unreachable", "schema": "unknown", "error": type(error).__name__}

    return {
        "database": "ok",
        "schema": "current" if current == head else "outdated",
        "revision": current,
        "head": head,
    }
