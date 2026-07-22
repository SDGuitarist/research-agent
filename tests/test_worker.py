"""Session 6 worker + reaper tests against real, committed Postgres rows.

The claim/finish/reap guarantees are cross-connection and cross-transaction, so
these use the ``committed_db`` fixture (real commits + TRUNCATE afterward), NOT
the rollback ``db`` fixture — rollback isolation cannot express SKIP LOCKED or a
report surviving a committed finish.
"""

import threading
import uuid

import pytest

from research_agent import worker
from research_agent.results import ResearchResult
from research_agent.worker import (
    ClaimLost,
    claim_next_job,
    fail_job,
    finish_job,
    reap_stale_jobs,
)


# --- helpers (explicit transactions so writes commit and reads don't linger) ---

def _insert_job(conn, query, *, mode="quick", max_attempts=3):
    with conn.transaction():
        return conn.execute(
            """INSERT INTO jobs (query, mode, max_attempts)
               VALUES (%s, %s, %s) RETURNING *""",
            (query, mode, max_attempts),
        ).fetchone()


def _fetch_job(conn, job_id):
    with conn.transaction():
        return conn.execute("SELECT * FROM jobs WHERE id = %s", (job_id,)).fetchone()


def _count_reports(conn, job_id):
    with conn.transaction():
        return conn.execute(
            "SELECT count(*) AS n FROM reports WHERE job_id = %s", (job_id,)
        ).fetchone()["n"]


def _force_stale(conn, job_id, seconds=3600):
    with conn.transaction():
        conn.execute(
            "UPDATE jobs SET heartbeat_at = now() - make_interval(secs => %s) WHERE id = %s",
            (seconds, job_id),
        )


def _result(report="# Report", *, query="specific market analysis", mode="quick"):
    return ResearchResult(
        report=report, query=query, mode=mode, sources_used=3, status="full_report"
    )


@pytest.fixture
def app_pool(committed_db, database_url):
    """Open the worker's module-global pool against the same test DB that
    ``committed_db`` reads, so ``pooled_connection()``-based code (heartbeat,
    finish, poll_once) and the assertions share one database. ``committed_db``
    truncates the queue tables; the autouse ``_reset_db_pool`` closes the app
    pool before the next test."""
    from research_agent import db as db_module

    db_module.open_pool(database_url)
    return committed_db  # the pool used for setup + assertions


# --- claim ---

def test_claim_sets_running_and_increments_attempts(committed_db):
    pool = committed_db
    with pool.connection() as conn:
        job = _insert_job(conn, "specific market analysis")
        assert job["status"] == "queued" and job["attempts"] == 0

        claimed = claim_next_job(conn)
        assert claimed["id"] == job["id"]
        assert claimed["status"] == "running"
        assert claimed["attempts"] == 1
        assert claimed["claim_id"] is not None
        assert claimed["claimed_at"] is not None
        assert claimed["heartbeat_at"] is not None


def test_claim_returns_none_on_empty_queue(committed_db):
    with committed_db.connection() as conn:
        assert claim_next_job(conn) is None


def test_concurrent_claim_yields_a_single_winner(committed_db):
    """Two workers, one queued job → exactly one claims it (SKIP LOCKED)."""
    pool = committed_db
    with pool.connection() as conn:
        job = _insert_job(conn, "single contested query")

    barrier = threading.Barrier(2)
    results: list = []
    lock = threading.Lock()

    def contender():
        with pool.connection() as conn:
            barrier.wait()
            claimed = claim_next_job(conn)
        with lock:
            results.append(claimed)

    threads = [threading.Thread(target=contender) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    winners = [r for r in results if r is not None]
    assert len(winners) == 1
    assert winners[0]["id"] == job["id"]


# --- finish ---

def test_finish_marks_done_and_writes_one_report(committed_db):
    pool = committed_db
    with pool.connection() as conn:
        job = _insert_job(conn, "specific market analysis")
        claimed = claim_next_job(conn)
        report_key = finish_job(conn, claimed, _result("# Done"))

    with pool.connection() as conn:
        assert _fetch_job(conn, job["id"])["status"] == "done"
        assert _count_reports(conn, job["id"]) == 1
        stored = conn.execute(
            "SELECT report_key, content FROM reports WHERE job_id = %s", (job["id"],)
        ).fetchone()
    assert stored["report_key"] == report_key
    assert stored["content"] == "# Done"


def test_finish_retry_raises_claim_lost_no_duplicate_report(committed_db):
    """Re-finishing an already-done job creates no second report."""
    pool = committed_db
    with pool.connection() as conn:
        job = _insert_job(conn, "specific market analysis")
        claimed = claim_next_job(conn)
        finish_job(conn, claimed, _result())

    with pool.connection() as conn:
        with pytest.raises(ClaimLost):
            finish_job(conn, claimed, _result("# Second"))

    with pool.connection() as conn:
        assert _count_reports(conn, job["id"]) == 1


def test_lost_claim_finish_leaves_no_orphan_report(committed_db):
    """A worker whose claim was reaped/re-claimed cannot persist a report."""
    pool = committed_db
    with pool.connection() as conn:
        job = _insert_job(conn, "lost claim scenario")
        worker_a = claim_next_job(conn)  # claim_id A

    # Lease expires → reaper requeues → worker B claims (claim_id B).
    with pool.connection() as conn:
        _force_stale(conn, job["id"])
        assert reap_stale_jobs(conn, lease_seconds=1) == 1
        worker_b = claim_next_job(conn)
    assert worker_b["claim_id"] != worker_a["claim_id"]

    # Worker B finishes legitimately.
    with pool.connection() as conn:
        finish_job(conn, worker_b, _result("# B wins"))

    # The outrun worker A tries to finish with its stale claim.
    with pool.connection() as conn:
        with pytest.raises(ClaimLost):
            finish_job(conn, worker_a, _result("# A orphan"))

    with pool.connection() as conn:
        assert _count_reports(conn, job["id"]) == 1  # only B's report
        done = _fetch_job(conn, job["id"])
        assert done["status"] == "done"
        content = conn.execute(
            "SELECT content FROM reports WHERE job_id = %s", (job["id"],)
        ).fetchone()["content"]
    assert content == "# B wins"


# --- fail ---

def test_fail_job_sets_failed_with_error_and_no_report(committed_db):
    pool = committed_db
    with pool.connection() as conn:
        job = _insert_job(conn, "specific market analysis")
        claimed = claim_next_job(conn)
        assert fail_job(conn, claimed, "boom") is True

    with pool.connection() as conn:
        row = _fetch_job(conn, job["id"])
        assert row["status"] == "failed"
        assert row["error"] == "boom"
        assert _count_reports(conn, job["id"]) == 0


def test_fail_job_with_lost_claim_returns_false(committed_db):
    pool = committed_db
    with pool.connection() as conn:
        job = _insert_job(conn, "specific market analysis")
        claimed = claim_next_job(conn)
        stale = dict(claimed, claim_id=uuid.uuid4())  # someone else owns it now
        assert fail_job(conn, stale, "boom") is False
        assert _fetch_job(conn, job["id"])["status"] == "running"


# --- reaper ---

def test_reaper_requeues_stale_running_job(committed_db):
    pool = committed_db
    with pool.connection() as conn:
        job = _insert_job(conn, "specific market analysis")
        claim_next_job(conn)  # running, attempts=1
        _force_stale(conn, job["id"])
        assert reap_stale_jobs(conn, lease_seconds=1) == 1

        row = _fetch_job(conn, job["id"])
        assert row["status"] == "queued"
        assert row["claim_id"] is None
        assert row["heartbeat_at"] is None
        assert row["attempts"] == 1  # reaper does not touch attempts


def test_reaper_fails_job_past_max_attempts(committed_db):
    pool = committed_db
    with pool.connection() as conn:
        job = _insert_job(conn, "specific market analysis", max_attempts=1)
        claim_next_job(conn)  # attempts=1 == max_attempts
        _force_stale(conn, job["id"])
        assert reap_stale_jobs(conn, lease_seconds=1) == 1

        row = _fetch_job(conn, job["id"])
        assert row["status"] == "failed"
        assert row["error"]


def test_reaper_leaves_fresh_running_job_untouched(committed_db):
    pool = committed_db
    with pool.connection() as conn:
        job = _insert_job(conn, "specific market analysis")
        claim_next_job(conn)  # heartbeat_at = now(), fresh
        assert reap_stale_jobs(conn, lease_seconds=90) == 0
        assert _fetch_job(conn, job["id"])["status"] == "running"


# --- heartbeat guard ---

def test_beat_advances_and_guards_on_claim_id(committed_db):
    pool = committed_db
    with pool.connection() as conn:
        job = _insert_job(conn, "heartbeat guard query")
        claimed = claim_next_job(conn)
        before = _fetch_job(conn, job["id"])["heartbeat_at"]

        assert worker._beat(conn, job["id"], claimed["claim_id"]) == 1  # rightful owner
        assert worker._beat(conn, job["id"], uuid.uuid4()) == 0  # zombie claim no-ops

        after = _fetch_job(conn, job["id"])["heartbeat_at"]
    assert after >= before


# --- integration: enqueue → process_one → done + report (stubbed research) ---

async def _fake_research(query, mode="standard", **kwargs):
    return ResearchResult(
        report=f"# Report for {query}", query=query, mode=mode,
        sources_used=2, status="full_report",
    )


def test_process_one_runs_job_to_done_with_report(app_pool, monkeypatch):
    pool = app_pool
    monkeypatch.setattr(worker, "run_research_async", _fake_research)
    with pool.connection() as conn:
        job = _insert_job(conn, "integration specific query", mode="standard")

    with worker.pooled_connection() as conn:  # app pool (autocommit)
        claimed = claim_next_job(conn)
    worker.process_one(claimed, heartbeat_interval=0.02)

    with pool.connection() as conn:
        done = _fetch_job(conn, job["id"])
        assert done["status"] == "done"
        assert _count_reports(conn, job["id"]) == 1
        content = conn.execute(
            "SELECT content FROM reports WHERE job_id = %s", (job["id"],)
        ).fetchone()["content"]
    assert content == "# Report for integration specific query"


def test_process_one_marks_failed_on_research_error(app_pool, monkeypatch):
    pool = app_pool

    async def _boom(query, mode="standard", **kwargs):
        from research_agent.errors import SearchError
        raise SearchError("search backend down")

    monkeypatch.setattr(worker, "run_research_async", _boom)
    with pool.connection() as conn:
        job = _insert_job(conn, "failing specific query", mode="standard")

    with worker.pooled_connection() as conn:
        claimed = claim_next_job(conn)
    worker.process_one(claimed, heartbeat_interval=0.02)

    with pool.connection() as conn:
        row = _fetch_job(conn, job["id"])
        assert row["status"] == "failed"
        assert "search backend down" in row["error"]
        assert _count_reports(conn, job["id"]) == 0


def test_poll_once_claims_and_processes(app_pool, monkeypatch):
    pool = app_pool
    monkeypatch.setattr(worker, "run_research_async", _fake_research)
    with pool.connection() as conn:
        job = _insert_job(conn, "poll cycle specific query", mode="standard")

    assert worker.poll_once(heartbeat_interval=0.02) is True

    with pool.connection() as conn:
        assert _fetch_job(conn, job["id"])["status"] == "done"
        assert _count_reports(conn, job["id"]) == 1


def test_poll_once_returns_false_when_queue_empty(app_pool):
    assert worker.poll_once(heartbeat_interval=0.02) is False


def test_run_forever_exits_when_stop_is_set():
    """The SIGTERM handler sets this event; a set stop ends the loop promptly
    (loop body never runs, so no pool/DB is needed)."""
    stop = threading.Event()
    stop.set()
    worker.run_forever(stop=stop, poll_idle=0.01)  # returns immediately
