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
