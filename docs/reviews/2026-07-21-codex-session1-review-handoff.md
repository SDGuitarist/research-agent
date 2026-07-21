# Codex Code Review — Phase A, Session 1 (DB Foundation)

External code review (fresh context) for a compound-engineering Work → Review loop. Be adversarial and specific. This is a **single-user internal tool** — flag over-engineering (YAGNI) as readily as bugs.

## Repo & diff
- Repo: `research-agent` (Python 3.14; a CLI + MCP web-research agent).
- Branch: `feat/headless-service-core`. **Review the Session 1 commit:** `git show 3a379c0` (or `git diff e992bf3..3a379c0`).
- Plan context: `docs/plans/2026-07-21-feat-headless-service-core-plan.md` (Session 1 + "Implementation Notes" §1–§5).

## What Session 1 built (files→Postgres foundation — additive only, nothing rewired yet)
- `research_agent/config.py` — `Settings` + `require_database_url()` (fail-fast), one `.env` seam.
- `research_agent/db.py` — psycopg3 `ConnectionPool` for Supabase **session pooler (5432)**: `open=False`+`.open()`, `check_connection`, `dict_row`, `autocommit=True`, `min/max=1/2`, module-global `_pool` + `atexit`.
- `research_agent/migrate.py` — dependency-free runner: `schema_migrations` + `pg_advisory_lock` (on a direct 5432 conn), per-file transaction, idempotent, ordered `NNN_*.sql`.
- `migrations/001_init.sql` — `jobs`, `reports`, `gaps`, `gap_audit`, `critiques` (+ status `CHECK`s, `UNIQUE(job_id)`, `UNIQUE(report_key)`, `claim_id`/`heartbeat_at`, partial indexes).
- `research_agent/errors.py` — `+ConfigError(ResearchError)`.
- `tests/conftest.py` — opt-in Postgres fixtures: rollback-per-test `db`, `committed_db` (TRUNCATE), session pool, testcontainers fallback, autouse `_reset_db_pool`.
- `tests/test_{config,migrate,db}.py` — 13 tests. Full suite **1134 pass**; MCP lint 8/8. DB tests run on a real Postgres via testcontainers.

## Scrutinize (return P0/P1/P2 with file:line + a one-line fix)
1. **`migrate.py` robustness.** It relies on psycopg3 `conn.execute(whole_file_sql)` running *multiple* statements. Is that guaranteed, or will it break for a future migration with dollar-quoted function bodies or `CREATE INDEX CONCURRENTLY` (can't run inside a transaction)? Is the session advisory lock held correctly across the per-file transactions on an autocommit connection, and released on every error path? Any window where two concurrent runners both treat a file as pending?
2. **`db.py` pool.** Is the session-pooler + `autocommit=True` + "callers use `with conn.transaction()`" contract sound? Is `open_pool` safe under concurrent first-callers (FastAPI threadpool + worker + heartbeat thread)? Module-global `_pool` + `atexit` + the autouse test reset — any leak or cross-test contamination? Is `max_size=2` enough once a heartbeat thread *also* borrows a connection during a job (Session 6)?
3. **`001_init.sql`.** Constraint completeness vs. the plan checklist. `UNIQUE(job_id)` is nullable (Postgres allows multiple NULLs) — correct for CLI/MCP reports? Should `reports.mode` carry a `CHECK` like `jobs.mode`? Is the `gen_random_uuid()` (PG13+ core) assumption safe on Supabase? Any missing index/constraint Session 2+ will need? `gap_audit` is "INSERT-only by contract" — enforce (trigger/REVOKE) or is code-level fine for one user?
4. **conftest fixtures.** Is the rollback-per-test `db` fixture correct (`raise psycopg.Rollback` inside `with conn.transaction()`)? Does the autouse `_reset_db_pool` (runs for *all* 1134 tests) add real risk or just overhead? Is the disposable-URL guard strong enough? `postgres:16-alpine` vs Supabase's PG version — any drift that lets a bug pass here but fail in prod?
5. **`config.py`.** Fail-fast placement (pool-open vs import). Does `ConfigError(ResearchError)` risk a downstream `except ResearchError` swallowing a startup misconfig? The `_dotenv_loaded` global + "load_dotenv doesn't override existing env" semantics — any surprise?
6. **Session 2 readiness.** Does this foundation cleanly support the next step — the injected-`conn` storage rewrite (`load_schema`/`save_schema`/`log_flip` → per-gap rows), keeping the pure gap functions untouched? Any friction or missing helper?
7. **Scope / YAGNI.** Over-built or missing anything for Session 1's DoD (buildable/testable while parked on Tavily)?

## Return format
Prioritized findings — **P0** (breaks correctness / blocks), **P1** (silent corruption / bad UX), **P2** (specify / nice-to-have) — each with file:line and a one-line fix. State explicitly whether the foundation is sound to build Session 2 on, or if something must change first.
