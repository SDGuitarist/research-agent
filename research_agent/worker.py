"""Background worker: a sync poll loop that drains the Postgres job queue.

The web service only enqueues ``jobs`` rows; this process claims them and runs
the 30-180s research pipeline out-of-band, so the work outlives the request and
survives restarts (Phase A's reframing requirement).

Design (see the plan's "transaction boundaries" and Implementation Notes §1):

- **Claim** in a short transaction with ``FOR UPDATE SKIP LOCKED`` so two workers
  never grab the same job; ``attempts`` is incremented here so poison jobs hit
  their cap.
- **Run** ``asyncio.run(run_research_async(...))`` per job — NEVER inside the claim
  transaction (idle-in-transaction pins a pooler backend). A daemon heartbeat
  thread ticks ``heartbeat_at`` concurrently so the reaper's lease only needs to
  exceed the heartbeat interval, not the runtime.
- **Finish** in one transaction: an owner-checked ``UPDATE`` guarded on rowcount,
  then the report INSERT. If the claim was lost (0 rows) we raise :class:`ClaimLost`
  and the whole transaction rolls back, so no orphan report survives for a job
  this worker no longer owns.
- **Reaper** requeues ``running`` jobs whose lease expired (→ ``failed`` past
  ``max_attempts``); run here as a poll-loop step (pg_cron is an optional Phase C
  swap).

Every DB helper takes an injected ``conn`` and owns its own short transaction, so
behaviour is identical whether the connection is autocommit (the production pool)
or a test connection.  The pipeline itself is untouched.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from typing import Any

from research_agent import run_research_async
from research_agent.db import close_pool, open_pool, pooled_connection
from research_agent.errors import ConfigError, ResearchError, StateError
from research_agent.report_store import save_report
from research_agent.results import ResearchResult

logger = logging.getLogger(__name__)

# Heartbeat ~ every 20s (between the plan's 15-30s); the reaper lease (90s) only
# needs to exceed one heartbeat interval to tell "still alive" from "abandoned".
HEARTBEAT_INTERVAL_SECONDS = 20.0
LEASE_SECONDS = 90
# Idle poll backoff (plan: 2-5s). Not a busy loop; the queued partial index makes
# the empty-queue claim cheap.
POLL_IDLE_SECONDS = 3.0

Job = dict[str, Any]


class ClaimLost(Exception):
    """The worker no longer owns the job it tried to finish.

    The owner-checked finish ``UPDATE`` matched 0 rows: the job was requeued,
    failed, or re-claimed (typically by the reaper after a lease expiry). Raised
    inside the finish transaction so the rollback drops the would-be report —
    this is what enforces ``report exists ⇔ job is 'done', by its rightful
    owner``. ``UNIQUE(job_id)`` only stops duplicates, not orphans.
    """


# --- Queue operations (each owns a short transaction) ---

_CLAIM_SQL = """
    UPDATE jobs
       SET status = 'running',
           attempts = attempts + 1,
           claim_id = gen_random_uuid(),
           claimed_at = now(),
           heartbeat_at = now()
     WHERE id = (
         SELECT id FROM jobs
          WHERE status = 'queued'
          ORDER BY created_at
          FOR UPDATE SKIP LOCKED
          LIMIT 1
     )
     RETURNING *
"""


def claim_next_job(conn) -> Job | None:
    """Atomically claim the oldest queued job, or return ``None`` if none.

    ``SKIP LOCKED`` means concurrent workers never claim the same row. The whole
    statement is one short transaction — the lock is released the moment it
    commits, so the agent never runs while a row lock is held.
    """
    with conn.transaction():
        return conn.execute(_CLAIM_SQL).fetchone()


def finish_job(conn, job: Job, result: ResearchResult) -> str:
    """Owner-checked finish in ONE transaction; return the saved report_key.

    The ``UPDATE`` runs first and is guarded on rowcount: if the claim is gone we
    raise :class:`ClaimLost`, which rolls the transaction back before the report
    is ever inserted. Persisting the report and flipping the job to ``done`` are
    therefore atomic and only happen for the job's rightful owner.
    """
    with conn.transaction():
        cur = conn.execute(
            """UPDATE jobs SET status = 'done', finished_at = now()
                WHERE id = %s AND claim_id = %s AND status = 'running'""",
            (job["id"], job["claim_id"]),
        )
        if cur.rowcount == 0:
            raise ClaimLost(job["id"])
        # Shares the finish transaction (save_report opens a nested savepoint);
        # a job_id collision here is an invariant breach and rolls the whole
        # thing back rather than duplicating a report.
        return save_report(
            conn,
            query=job["query"],
            mode=job["mode"],
            content=result.report,
            gate_decision=result.status,
            sources_used=result.sources_used,
            job_id=job["id"],
        )


def fail_job(conn, job: Job, error: str) -> bool:
    """Owner-checked failure. Return ``False`` if the claim was already lost.

    Never writes a partial report. Owner-checked so a zombie worker cannot stomp
    a job the reaper already handed to someone else.
    """
    with conn.transaction():
        cur = conn.execute(
            """UPDATE jobs SET status = 'failed', error = %s, finished_at = now()
                WHERE id = %s AND claim_id = %s AND status = 'running'""",
            (error, job["id"], job["claim_id"]),
        )
    return cur.rowcount > 0


def reap_stale_jobs(conn, lease_seconds: int = LEASE_SECONDS) -> int:
    """Requeue running jobs whose lease expired (→ failed past max_attempts).

    The lease is a staleness window on ``heartbeat_at``. Requeue and fail have
    disjoint ``attempts`` predicates, so the two statements never touch the same
    row. Returns the number of jobs handled.
    """
    with conn.transaction():
        requeued = conn.execute(
            """UPDATE jobs
                  SET status = 'queued', claim_id = NULL,
                      claimed_at = NULL, heartbeat_at = NULL
                WHERE status = 'running'
                  AND heartbeat_at < now() - make_interval(secs => %s)
                  AND attempts < max_attempts""",
            (lease_seconds,),
        ).rowcount
        failed = conn.execute(
            """UPDATE jobs
                  SET status = 'failed', finished_at = now(),
                      error = 'Abandoned: worker lease expired past max attempts.'
                WHERE status = 'running'
                  AND heartbeat_at < now() - make_interval(secs => %s)
                  AND attempts >= max_attempts""",
            (lease_seconds,),
        ).rowcount
    return requeued + failed


# --- Heartbeat (runs concurrently with the blocking research call) ---

def _beat(conn, job_id: uuid.UUID, claim_id: uuid.UUID) -> int:
    """Touch ``heartbeat_at`` for a still-owned running job; return rows updated.

    The ``claim_id`` guard makes a requeued job's zombie heartbeat match 0 rows —
    it can't resurrect a claim the reaper already took away.
    """
    with conn.transaction():
        return conn.execute(
            """UPDATE jobs SET heartbeat_at = now()
                WHERE id = %s AND claim_id = %s AND status = 'running'""",
            (job_id, claim_id),
        ).rowcount


def _heartbeat_loop(
    job_id: uuid.UUID, claim_id: uuid.UUID, stop: threading.Event, interval: float
) -> None:
    """Tick ``heartbeat_at`` every ``interval`` seconds until ``stop`` is set.

    ``stop.wait`` returns True the moment the run finishes, so the loop exits
    promptly; the claim already set ``heartbeat_at`` so the first tick can wait a
    full interval. A transient DB error skips one tick rather than killing the run.
    """
    while not stop.wait(interval):
        try:
            with pooled_connection() as conn:
                _beat(conn, job_id, claim_id)
        except (StateError, ConfigError) as exc:
            logger.warning("Heartbeat skipped for job %s: %s", job_id, exc)


def _stop_heartbeat(stop: threading.Event, thread: threading.Thread) -> None:
    stop.set()
    thread.join(timeout=5)


# --- Per-job orchestration ---

def process_one(job: Job, *, heartbeat_interval: float = HEARTBEAT_INTERVAL_SECONDS) -> None:
    """Run one claimed job to a terminal state, heart-beating throughout.

    The heartbeat is stopped before the terminal DB write, so no tick races the
    finish/fail ``UPDATE``. All persistence failures are swallowed and logged —
    the reaper requeues anything left ``running``.
    """
    job_id = job["id"]
    stop = threading.Event()
    heartbeat = threading.Thread(
        target=_heartbeat_loop,
        args=(job_id, job["claim_id"], stop, heartbeat_interval),
        name=f"heartbeat-{job_id}",
        daemon=True,
    )
    heartbeat.start()
    try:
        result = asyncio.run(run_research_async(job["query"], mode=job["mode"]))
        outcome: tuple[str, Any] = ("finish", result)
    except ResearchError as exc:
        logger.warning("Job %s failed: %s", job_id, exc)
        outcome = ("fail", str(exc))
    except Exception:
        # Worker-loop boundary: one bad job must never crash the long-running
        # process. Mark it failed with a generic reason and keep polling. This
        # is the single justified broad catch (mirrors the MCP server boundary,
        # per CLAUDE.md "Never bare except Exception").
        logger.exception("Unexpected error running job %s", job_id)
        outcome = ("fail", "Worker error while running research.")
    finally:
        _stop_heartbeat(stop, heartbeat)

    if outcome[0] == "finish":
        _safe_finish(job, outcome[1])
    else:
        _safe_fail(job, outcome[1])


def _safe_finish(job: Job, result: ResearchResult) -> None:
    try:
        with pooled_connection() as conn:
            report_key = finish_job(conn, job, result)
        logger.info("Job %s done → report %s", job["id"], report_key)
    except ClaimLost:
        logger.warning(
            "Claim lost for job %s; discarding result (reaper or a newer worker owns it).",
            job["id"],
        )
    except (StateError, ConfigError) as exc:
        logger.error(
            "Could not persist finish for job %s (%s); reaper will requeue it.",
            job["id"], exc,
        )


def _safe_fail(job: Job, reason: str) -> None:
    try:
        with pooled_connection() as conn:
            if not fail_job(conn, job, reason):
                logger.warning("Could not fail job %s: claim already lost.", job["id"])
    except (StateError, ConfigError) as exc:
        logger.error(
            "Could not mark job %s failed (%s); reaper will requeue it.",
            job["id"], exc,
        )


# --- Poll loop ---

def poll_once(
    *,
    heartbeat_interval: float = HEARTBEAT_INTERVAL_SECONDS,
    lease_seconds: int = LEASE_SECONDS,
) -> bool:
    """Reap stale jobs, then claim and process one. Return True if work was done.

    DB errors during reap/claim are logged and swallowed (the caller backs off),
    so a transient outage never crashes the loop.
    """
    try:
        with pooled_connection() as conn:
            reaped = reap_stale_jobs(conn, lease_seconds)
        if reaped:
            logger.info("Reaper handled %d stale job(s).", reaped)
        with pooled_connection() as conn:
            job = claim_next_job(conn)
    except (StateError, ConfigError) as exc:
        logger.error("Poll cycle DB error (%s); backing off.", exc)
        return False

    if job is None:
        return False
    logger.info(
        "Claimed job %s (%s, attempt %d).", job["id"], job["mode"], job["attempts"]
    )
    process_one(job, heartbeat_interval=heartbeat_interval)
    return True


def run_forever(
    *,
    poll_idle: float = POLL_IDLE_SECONDS,
    heartbeat_interval: float = HEARTBEAT_INTERVAL_SECONDS,
    lease_seconds: int = LEASE_SECONDS,
    stop: threading.Event | None = None,
) -> None:
    """Poll until ``stop`` is set (or forever). Idle sleeps are interruptible."""
    stop = stop or threading.Event()
    logger.info("Worker started; polling every %.1fs when idle.", poll_idle)
    while not stop.is_set():
        did_work = poll_once(
            heartbeat_interval=heartbeat_interval, lease_seconds=lease_seconds
        )
        if not did_work:
            stop.wait(poll_idle)


def main() -> None:
    """Entry point for the research-agent-worker console script."""
    import signal

    from research_agent.config import get_settings

    settings = get_settings()  # loads .env once
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # API keys are validated at point of use (a keyless worker fails each job with
    # a clear error rather than refusing to boot), but warn loudly at startup so a
    # misconfigured deploy is obvious in the logs instead of silently failing jobs.
    for name, value in (
        ("ANTHROPIC_API_KEY", settings.anthropic_api_key),
        ("TAVILY_API_KEY", settings.tavily_api_key),
    ):
        if not value:
            logger.warning("%s is not set — jobs will fail until it is configured.", name)

    open_pool()  # fail fast if DATABASE_URL is missing or Postgres is unreachable

    stop = threading.Event()

    def _request_shutdown(signum, _frame):
        # SIGTERM (e.g. a Railway redeploy): stop after the current poll finishes.
        # A job already running keeps running to completion; if the platform
        # SIGKILLs before it finishes, the reaper requeues it on the next instance.
        logger.info("Signal %s received; shutting down after the current poll.", signum)
        stop.set()

    signal.signal(signal.SIGTERM, _request_shutdown)

    try:
        run_forever(stop=stop)
    except KeyboardInterrupt:  # local Ctrl-C: stop promptly
        logger.info("Worker interrupted; shutting down.")
    finally:
        close_pool()


if __name__ == "__main__":  # pragma: no cover
    main()
