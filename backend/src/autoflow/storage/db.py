"""
Database engine, sessions and shared column types.

The same code runs on SQLite (development) and PostgreSQL (production);
the target is chosen with DATABASE_URL.
"""

from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import DateTime, MetaData, create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.types import TypeDecorator

from autoflow import config


engine = create_engine(config.DATABASE_URL)

if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def _configure_sqlite(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        # Write-ahead logging: faster commits, readers do not block writers
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for every AutoFlow table."""

    # Predictable constraint names, so migrations can always refer to them
    # (unique constraints are named explicitly where they are declared)
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    })


class UTCDateTime(TypeDecorator):
    """Store datetimes in UTC and always return them timezone-aware."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        # SQLite drops the timezone, so restore it
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


def utc_now():
    return datetime.now(timezone.utc)


@contextmanager
def session_scope():
    """Provide a transactional session for code outside the API."""

    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
