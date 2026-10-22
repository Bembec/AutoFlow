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
