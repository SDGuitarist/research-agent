"""Postgres connection pool (psycopg3) — shared by CLI, MCP, web, and worker.

Sized for a single-user tool against Supabase's **session pooler** (port 5432):
a small pool, connections validated on checkout, ``dict_row`` rows, and
``autocommit=True`` so callers opt into atomic units explicitly via
``with conn.transaction():``.  The storage layer takes an injected connection —
this module only owns the pool's lifecycle.
"""

from __future__ import annotations

import atexit

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import require_database_url

# Small pool: one user, ~5 processes (web, worker, CLI, MCP, reaper) sharing
# Supabase's connection cap. Sum of max_size across processes must stay under it.
POOL_MIN_SIZE = 1
POOL_MAX_SIZE = 2

_pool: ConnectionPool | None = None


def _make_pool(conninfo: str) -> ConnectionPool:
    return ConnectionPool(
        conninfo=conninfo,
        min_size=POOL_MIN_SIZE,
        max_size=POOL_MAX_SIZE,
        max_idle=60,
        timeout=10,
        # Poolers recycle idle backends — validate before handing one out.
        check=ConnectionPool.check_connection,
        kwargs={"row_factory": dict_row, "autocommit": True},
        open=False,
        name="research-agent-pool",
    )


def open_pool(conninfo: str | None = None) -> ConnectionPool:
    """Open the shared pool (idempotent). Fails fast if the DB is unreachable."""
    global _pool
    if _pool is None:
        pool = _make_pool(conninfo or require_database_url())
        pool.open(wait=True, timeout=30)
        _pool = pool
    return _pool


def get_pool() -> ConnectionPool:
    """Return the open pool, or raise if :func:`open_pool` was never called."""
    if _pool is None:
        raise RuntimeError("Connection pool is not open; call open_pool() at startup.")
    return _pool


def close_pool() -> None:
    """Close the shared pool if open (idempotent)."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


atexit.register(close_pool)
