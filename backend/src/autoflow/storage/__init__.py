"""Persistence layer for AutoFlow."""


def initialize_storage():
    """Create every database table AutoFlow needs."""

    from autoflow.storage.approvals import initialize_approvals_table
    from autoflow.storage.database import initialize_database

    initialize_database()
    initialize_approvals_table()
