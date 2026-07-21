"""Dependency-free SQL migration runner (no Alembic).

Applies ordered ``migrations/NNN_*.sql`` files exactly once, tracked in a
``schema_migrations`` table, serialized across concurrent processes with a
session-level advisory lock.

Run against the Supabase **direct/session** endpoint (port 5432), never the
transaction pooler — the advisory lock needs a sticky session connection.
Invoke as ``python -m research_agent.migrate`` (uses ``MIGRATION_DATABASE_URL``
if set, else ``DATABASE_URL``).
"""

from __future__ import annotations

import os
import pathlib

import psycopg
from psycopg.rows import dict_row

# migrations/ lives at the repo root (one level above the package directory).
MIGRATIONS_DIR = pathlib.Path(__file__).resolve().parent.parent / "migrations"

# Arbitrary app-specific constant used to serialize concurrent migration runs.
ADVISORY_LOCK_KEY = 727312


def migration_files(migrations_dir: pathlib.Path = MIGRATIONS_DIR) -> list[pathlib.Path]:
    """Return migration files sorted by their zero-padded ``NNN_`` prefix.

    Only ``NNN_*.sql`` names are considered, so notes/READMEs are ignored.
    Zero-padded prefixes sort lexically = numerically up to 999.
    """
    return sorted(migrations_dir.glob("[0-9][0-9][0-9]_*.sql"))


def pending_migrations(
    files: list[pathlib.Path], applied: set[str]
) -> list[pathlib.Path]:
    """Return the files whose names are not yet recorded as applied."""
    return [f for f in files if f.name not in applied]


def _ensure_migrations_table(conn: psycopg.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version text PRIMARY KEY,"
        " applied_at timestamptz NOT NULL DEFAULT now())"
    )


def run_migrations(
    direct_dsn: str, migrations_dir: pathlib.Path = MIGRATIONS_DIR
) -> list[str]:
    """Apply pending migrations in order. Idempotent + concurrency-safe.

    Pass a DIRECT/session DSN (Supabase port 5432), NOT the 6543 pooler.
    Each file runs in its own transaction. Returns the filenames applied by
    this call (empty if the DB was already up to date).
    """
    applied_now: list[str] = []
    # autocommit so the session advisory lock is held across the per-file txns.
    with psycopg.connect(direct_dsn, autocommit=True, row_factory=dict_row) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (ADVISORY_LOCK_KEY,))
        try:
            _ensure_migrations_table(conn)
            applied = {
                row["version"]
                for row in conn.execute(
                    "SELECT version FROM schema_migrations"
                ).fetchall()
            }
            for path in pending_migrations(migration_files(migrations_dir), applied):
                sql = path.read_text(encoding="utf-8")
                with conn.transaction():
                    conn.execute(sql)
                    conn.execute(
                        "INSERT INTO schema_migrations (version) VALUES (%s)",
                        (path.name,),
                    )
                applied_now.append(path.name)
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK_KEY,))
    return applied_now


def main() -> None:
    """Entry point for ``python -m research_agent.migrate``."""
    from .config import require_database_url

    dsn = os.environ.get("MIGRATION_DATABASE_URL") or require_database_url()
    applied = run_migrations(dsn)
    if applied:
        for name in applied:
            print(f"applied {name}")
    else:
        print("no pending migrations")


if __name__ == "__main__":
    main()
