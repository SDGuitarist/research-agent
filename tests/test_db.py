"""Integration tests for the DB foundation: pool, migrations, schema, constraints.

Require Docker (testcontainers) or a TEST_DATABASE_URL; skipped otherwise.
"""

import psycopg
import pytest

from tests.conftest import _assert_disposable_db_url


# --- disposable-DB guard (no database needed) ------------------------------

@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:p@localhost:5432/research_agent_test",
        "postgresql://u:p@db.example.com/test",
        "postgresql://u:p@host/app-test",
    ],
)
def test_disposable_guard_accepts_test_databases(url):
    _assert_disposable_db_url(url)  # must not raise


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:testpw@localhost:5432/research_agent",  # 'test' only in password
        "postgresql://u:p@localhost/maindb",                    # real local dev DB
        "postgresql://u:p@prod-host/app",
        "postgresql://u:p@host/",                               # empty database name
    ],
)
def test_disposable_guard_rejects_nondisposable(url):
    with pytest.raises(AssertionError):
        _assert_disposable_db_url(url)


def test_open_pool_is_thread_safe(monkeypatch):
    """Concurrent first-callers build the pool exactly once (no DB needed)."""
    import threading

    import research_agent.db as db_module

    db_module.close_pool()  # clean slate (the autouse fixture also does this)
    built: list[str] = []

    class _FakePool:
        def open(self, *a, **k):
            pass

        def close(self):
            pass

    def _fake_make(conninfo):
        built.append(conninfo)
        return _FakePool()

    monkeypatch.setattr(db_module, "_make_pool", _fake_make)

    barrier = threading.Barrier(8)
    results: list[object] = []

    def _worker():
        barrier.wait()  # release all threads together to maximise contention
        results.append(db_module.open_pool("postgresql://x/y"))

    threads = [threading.Thread(target=_worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(built) == 1, "pool must be built exactly once under contention"
    assert len({id(r) for r in results}) == 1, "all callers get the same pool"
    db_module.close_pool()


# --- pooled_connection error normalization (no database needed) ------------

def test_pooled_connection_yields_connection():
    """Happy path: the borrowed connection is handed straight through."""
    from contextlib import nullcontext
    from unittest.mock import patch

    from research_agent.db import pooled_connection

    sentinel = object()
    with patch("research_agent.db.open_pool") as mock_pool:
        mock_pool.return_value.connection.return_value = nullcontext(sentinel)
        with pooled_connection() as conn:
            assert conn is sentinel


def test_pooled_connection_normalizes_pool_timeout():
    """PoolTimeout (a psycopg error, not a ResearchError) becomes StateError so
    callers that only catch ResearchError don't leak it (Session 3 review P1)."""
    from unittest.mock import patch

    from psycopg_pool import PoolTimeout

    from research_agent.db import pooled_connection
    from research_agent.errors import StateError

    with patch("research_agent.db.open_pool", side_effect=PoolTimeout("exhausted")):
        with pytest.raises(StateError):
            with pooled_connection():
                pass


def test_pooled_connection_propagates_config_error():
    """A missing DATABASE_URL stays a ConfigError (already a ResearchError) — it
    must not be masked as a connection failure."""
    from unittest.mock import patch

    from research_agent.db import pooled_connection
    from research_agent.errors import ConfigError

    with patch("research_agent.db.open_pool", side_effect=ConfigError("no url")):
        with pytest.raises(ConfigError):
            with pooled_connection():
                pass


def test_db_roundtrip(db):
    assert db.execute("SELECT 1 AS n").fetchone()["n"] == 1


def test_all_tables_created(db):
    rows = db.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
    ).fetchall()
    names = {r["tablename"] for r in rows}
    expected = {"jobs", "reports", "gaps", "gap_audit", "critiques", "schema_migrations"}
    assert expected <= names


def test_run_migrations_is_idempotent(database_url, _db_setup):
    from research_agent.migrate import run_migrations

    # _db_setup already applied migrations once; a second run applies nothing.
    assert run_migrations(database_url) == []


def test_jobs_status_check_constraint(db):
    db.execute("INSERT INTO jobs (query, mode) VALUES ('q', 'quick')")
    # pytest.raises wraps the savepoint so the error rolls back to it and the
    # outer fixture transaction survives.
    with pytest.raises(psycopg.errors.CheckViolation):
        with db.transaction():
            db.execute(
                "INSERT INTO jobs (query, mode, status) VALUES ('q', 'quick', 'bogus')"
            )
    assert db.execute("SELECT count(*) AS c FROM jobs").fetchone()["c"] == 1


def test_reports_unique_job_id(db):
    job = db.execute(
        "INSERT INTO jobs (query, mode) VALUES ('q', 'quick') RETURNING id"
    ).fetchone()
    db.execute(
        "INSERT INTO reports (job_id, report_key, query, mode, content) "
        "VALUES (%s, 'k1', 'q', 'quick', 'c')",
        (job["id"],),
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        with db.transaction():
            db.execute(
                "INSERT INTO reports (job_id, report_key, query, mode, content) "
                "VALUES (%s, 'k2', 'q', 'quick', 'c')",
                (job["id"],),
            )
    assert db.execute("SELECT count(*) AS c FROM reports").fetchone()["c"] == 1


def test_report_key_unique(db):
    db.execute(
        "INSERT INTO reports (report_key, query, mode, content) "
        "VALUES ('same-key', 'q', 'quick', 'c')"
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        with db.transaction():
            db.execute(
                "INSERT INTO reports (report_key, query, mode, content) "
                "VALUES ('same-key', 'q2', 'quick', 'c2')"
            )
    assert db.execute("SELECT count(*) AS c FROM reports").fetchone()["c"] == 1
