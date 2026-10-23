"""Regression test: SQLite migrations must never delete data.

Batch migrations rebuild a SQLite table by copying it and dropping the old
one. With foreign keys enforced, that DROP used to cascade-delete every row
linked to the table (all memberships, workflows and runs of every
workspace). Migrations now run with enforcement off.
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def alembic(database, *args):
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{database.as_posix()}", "PYTHONPATH": str(BACKEND / "src")}
    result = subprocess.run([sys.executable, "-m", "alembic", *args], cwd=BACKEND, env=env,
                            capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stderr[-2000:]


def test_rebuilding_workspace_tables_keeps_linked_rows(tmp_path):
    database = tmp_path / "keep.db"
    alembic(database, "upgrade", "head")

    with sqlite3.connect(database) as db:
        db.execute("INSERT INTO users (id, email, name, password_hash, created_at) VALUES "
                   "(1, 'a@b.co', 'A', 'x', '2026-10-23 00:00:00')")
        db.execute("INSERT INTO workspaces (id, name, slug, created_at) VALUES (1, 'Shop', 'shop', '2026-10-23 00:00:00')")
        db.execute("INSERT INTO memberships (user_id, workspace_id, role, created_at) VALUES "
                   "(1, 1, 'owner', '2026-10-23 00:00:00')")
        db.execute("INSERT INTO workflows (workspace_id, name, description, status, created_at, updated_at) VALUES "
                   "(1, 'Flow', '', 'active', '2026-10-23 00:00:00', '2026-10-23 00:00:00')")

    # Down and up again through migrations that rebuild the workspaces table
    alembic(database, "downgrade", "0011")
    alembic(database, "upgrade", "head")

    with sqlite3.connect(database) as db:
        assert db.execute("SELECT count(*) FROM memberships").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM workflows").fetchone()[0] == 1
