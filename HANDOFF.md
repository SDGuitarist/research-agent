# HANDOFF — Research Agent

**Date:** 2026-07-21
**Phase:** Work — **Session 1 (Foundations) COMPLETE**; next is Session 2 (Gaps → DB)
**Branch:** `feat/headless-service-core` (not pushed) — 2 commits: planning docs + Session 1

## New arc: "Robust internal tool"

Turning the research-agent CLI into a **deployed internal web service** (FastAPI + Postgres-queue worker on Supabase/Railway). Chosen shape: **robust internal tool first** (not SaaS, not an embedded feature). This is **Phase A** (backend); Phase B = quality UI; Phase C = observability/cost-caps. Supersedes the Cycle 32 "parked" state — this new work is buildable/testable against mocked search while the Tavily key stays parked.

## What was done this session

- **Brainstorm** → [docs/brainstorms/2026-07-21-headless-service-core-brainstorm.md](docs/brainstorms/2026-07-21-headless-service-core-brainstorm.md) (reviewed + refined; added Definition of Done + watch-items).
- **Plan** → [docs/plans/2026-07-21-feat-headless-service-core-plan.md](docs/plans/2026-07-21-feat-headless-service-core-plan.md) (comprehensive; **deepened** with 5 parallel research agents → concrete snippets + doc URLs).
- **Codex plan-review handoff** → [docs/plans/2026-07-21-codex-plan-review-handoff.md](docs/plans/2026-07-21-codex-plan-review-handoff.md) (on clipboard, ready to paste into Codex).

## Key decisions (locked in the plan)

- Postgres-table queue + separate worker (2 Railway services, no Redis).
- Full storage cutover to Postgres/Supabase — **state only** (reports, gaps, gap_audit, critiques); `contexts/*.md` stay files. Migrate **gaps only**; old reports = disk archive.
- **Session pooler (5432)**; **sync psycopg3** storage with an **injected `conn`**; sync worker loop → `asyncio.run(research_async())` per job; async FastAPI with plain `def` routes.
- Mock seam: tests stub both search + Claude; **DoD smoke = mock search + live Claude** (~85% conf).
- **Minimal reaper** + heartbeat-decoupled lease + `claim_id`/`UNIQUE(job_id)` guards in Phase A (~80% conf).
- 7 sessions, **gaps-first** (Cycle 17 lesson). `verify_first: true`.

## Progress

- **Plan Review (Codex): DONE.** Two findings folded into the plan — P1 finish-txn orphan-report (raise/rollback on lost claim) and P2 `report_key` collision-proof derivation (`slug-{uuid8}`). Plus a self-review fix (heartbeat daemon thread). No P0/P1 remained.
- **Session 1 (Foundations): DONE** (commit `3a379c0`). Files: `config.py`, `db.py`, `migrate.py`, `migrations/001_init.sql`, `errors.py` (+`ConfigError`), `tests/conftest.py` (opt-in Postgres fixtures), `tests/test_{config,migrate,db}.py`. Deps added: `psycopg[binary,pool]`, `testcontainers[postgres]` (fastapi/uvicorn already present). DB tests run against a real Postgres via testcontainers (Docker).
- **Session 1 Code Review (Codex → fixes): DONE.** Applied 3 fixes — thread-safe `open_pool()` (double-checked lock), stricter test-DB disposability guard (checks the *database name*, not a URL substring), and correct pool-reset order (close-then-clear). +7 guard regression tests. **1141 tests pass; MCP lint 8/8.**

## Next: Session 2 — Gaps → DB (prove the state machine first; `verify_first`)

Rewrite `load_schema`/`save_schema`/`log_flip` to Postgres (per-gap rows), keep the pure functions (`mark_verified`/`mark_checked`/`detect_stale`/`select_batch`/`_parse_gap`) untouched, update `agent.py` (drop `schema_path`/`schema_path.parent`), and add `scripts/migrate_gaps.py` (idempotent, timestamp-preserving, post-import equality assertion). Storage functions take an **injected `conn`**.

## Three Questions (Work phase — Session 1)

1. **Hardest implementation decision?** Getting the rollback-per-test fixture right: the constraint tests initially left the transaction aborted (`InFailedSqlTransaction`) because `pytest.raises` was *inside* the savepoint. Fix: wrap the savepoint *with* `pytest.raises` so the error rolls the savepoint back and the outer fixture transaction survives. Also chose partial indexes over the composite queue index (per Impl. Notes §1).
2. **What did you consider changing but left alone?** Ripping out the scattered `os.environ.get`/`load_dotenv` sites to route everything through `config.py` now — left alone to keep Session 1 additive and non-breaking; that migration happens when the CLI/web/worker wire it in (Sessions 5–7). The existing `report_store`/`state` file code is likewise untouched (Sessions 2–3 migrate it).
3. **Least confident going into Session 2?** Whether the injected-`conn` rewrite of the gap I/O cleanly accommodates `agent.py`'s gap logic once `schema_path` disappears (the flagged blast radius), and whether `migrate.py`'s multi-statement `execute()` stays robust for a future migration containing dollar-quoted function bodies (worked fine for pure DDL).

### Prompt for Next Session (paste into a fresh conversation)

```
Read docs/plans/2026-07-21-feat-headless-service-core-plan.md — specifically "Implementation
Phases (Sessions)" → Session 2, the "Call-Site Inventory", "Implementation Notes" (§1 and §5),
and the "What must NOT change" + "Acceptance Tests (EARS)" sections. Also skim HANDOFF.md.

We are on branch feat/headless-service-core (nothing pushed). Session 1 (Foundations) is DONE
and reviewed — commits 3a379c0 → a13e2cd; 1141 tests pass; MCP lint 8/8. Implement ONLY
Session 2 (Gaps → DB) — the verify_first session — then commit and stop. Do NOT proceed to S3.

Session 1 gives you: config.py (get_settings/require_database_url), db.py (thread-safe psycopg3
pool: open_pool/get_pool/close_pool; session pooler 5432; dict_row; autocommit; INJECTED conn),
migrate.py, migrations/001_init.sql (the gaps + gap_audit tables ALREADY EXIST — do not edit 001;
add 002_*.sql only if truly needed), and conftest fixtures (db = rollback-per-test injected conn,
committed_db = TRUNCATE for concurrency, database_url = testcontainers; Docker is available).
Test cmd: python3 -m pytest tests/ -q.

Session 2 scope:
1. Rewrite gap I/O to Postgres with an INJECTED conn (caller owns the txn; never conn.commit()
   inside — use `with conn.transaction():`): schema.load_schema → load_gaps(conn) from the gaps
   table (keep SchemaResult/Gap/GapStatus types); state.save_schema → per-gap TARGETED upsert
   (NOT whole-doc rewrite — closes P0-5); staleness.log_flip → INSERT into gap_audit (preserve event_at).
2. Keep PURE functions byte-for-byte unchanged: mark_verified, mark_checked, detect_stale,
   select_batch, _parse_gap, and the dataclasses. Only the I/O boundary moves.
3. Update agent.py: drop self.schema_path + the `schema_path.parent / "gap_audit.log"` derivation
   (~line 168); gap-tracking guard becomes DB-based; thread a conn into gap load/save (~lines
   501, 193, 178, 176/185); wrap sync storage calls in asyncio.to_thread (pipeline is inside asyncio.run).
4. scripts/migrate_gaps.py — gaps-only import from gaps/pfe.yaml: validate via schema.py + cycle
   detection first; idempotent upsert keyed by gap id; PRESERVE original UTC timestamps (no re-stamp);
   post-import equality assertion (row count == YAML gap count; a gap's staleness verdict identical pre/post).
5. Migrate storage-coupled gap tests to the db fixture (test_state save/load, test_staleness log_flip,
   test_schema load, gap-state assertions in test_agent); pure-function tests stay unchanged; add
   migrate_gaps tests (idempotent re-run no-op; timestamp preservation; equality assertion).

Acceptance: gap state machine passes against Postgres; pfe gaps import + re-run is a no-op with
unchanged timestamps/state; a known gap's staleness verdict identical pre/post; full suite green;
MCP lint 8/8 (python3 scripts/lint_mcp_parity.py).

Guardrails: don't touch reports/critiques (S3) or the MCP server (S4); don't edit 001_init.sql
(add 002 if needed); follow "What must NOT change"; small commits. After committing Session 2,
stop and say DONE. Do NOT proceed to Session 3.

Session 1 review residuals (none block S2): disposable-DB guard is case-sensitive/convention-based;
open_pool doesn't close a half-open pool on failure (latent until S5–6).
```
