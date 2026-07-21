"""Postgres connection pool (psycopg3) — shared by CLI, MCP, web, and worker.

Sized for a single-user tool against Supabase's **session pooler** (port 5432):
a small pool, connections validated on checkout, ``dict_row`` rows, and
``autocommit=True`` so callers opt into atomic units explicitly via
``with conn.transaction():``.  The storage layer takes an injected connection —
this module only owns the pool's lifecycle.
"""

from __future__ import annotations

import atexit
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from psycopg import Connection, Error as PsycopgError
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import require_database_url
from .errors import StateError

# Small pool: one user, ~5 processes (web, worker, CLI, MCP, reaper) sharing
# Supabase's connection cap. Sum of max_size across processes must stay under it.
POOL_MIN_SIZE = 1
POOL_MAX_SIZE = 2

_pool: ConnectionPool | None = None
# Serializes pool init/teardown so concurrent startup callers (FastAPI
# threadpool + worker + heartbeat thread) can't build or clear it twice.
_pool_lock = threading.Lock()


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
    """Open the shared pool (idempotent, thread-safe). Fails fast if unreachable.

    Double-checked locking: skip the lock on the hot path once the pool exists,
    but serialize first-call initialization so two concurrent callers cannot
    each build (and leak) a pool.
    """
    global _pool
    if _pool is None:
        with _pool_lock:
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


@contextmanager
def pooled_connection() -> Iterator[Connection]:
    """Borrow a pooled connection, normalizing pool/connection failures to StateError.

    Opening the pool or checking out a connection can raise
    ``psycopg_pool.PoolTimeout`` (a ``psycopg.OperationalError`` subclass) when the
    database is unreachable. That is a psycopg error, not a ``ResearchError``, so a
    caller that only catches ``ResearchError`` would leak a raw traceback instead of
    following its declared error handling. Wrapping these boundary failures in
    ``StateError`` (a ``ResearchError`` subclass) lets every caller's contract apply:
    direct CLI operations fail fast with a clear message, and the optional-enhancement
    callers inside ``ResearchAgent`` catch it and degrade.

    A missing ``DATABASE_URL`` still surfaces as ``ConfigError`` (also a
    ``ResearchError``) from :func:`open_pool` and propagates unchanged. Query-level
    failures are normalized to ``StateError`` inside the storage functions, so they
    pass through here untouched.
    """
    try:
        with open_pool().connection() as conn:
            yield conn
    except PsycopgError as exc:
        raise StateError(f"Database connection failed: {exc}") from exc


def close_pool() -> None:
    """Close the shared pool if open (idempotent, thread-safe)."""
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.close()
            _pool = None


atexit.register(close_pool)
