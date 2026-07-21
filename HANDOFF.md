# HANDOFF — Research Agent

**Date:** 2026-07-21
**Phase:** Work — **Session 2 (Gaps → DB) COMPLETE**; next is independent Session 2 code review
**Branch:** `feat/headless-service-core` (not pushed) — Session 2 landed in `47e0bb1`, `eb43f5b`, `a032968`, `579db8f`

> ⚠️ **Concurrency note (2026-07-21):** Session 2 was worked by **two sessions in parallel** on
> this branch (a handoff that ran concurrently instead of sequentially). It resolved cleanly —
> the commits are non-overlapping and linear (`47e0bb1` production + `a032968` importer/pfe.yaml
> from one session; `eb43f5b` test migration from the other). **Lesson: run one writer per branch.**
> Before starting any follow-on session, confirm no other session/auto-continue is live on this branch.

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

## Session 2 — Gaps → DB: COMPLETE ✅ (`verify_first` satisfied)

- **`47e0bb1`** — gap I/O → Postgres: `schema.load_gaps(conn)`, `state.save_schema(conn, gaps)` (per-gap
  `ON CONFLICT ... IS DISTINCT FROM` upsert, closes P0-5), `staleness.log_flip(conn, ...)` → `gap_audit`
  (preserves `event_at`). `agent.py`: `schema_path` gone → `gap_tracking_enabled` flag; gap load/save
  threaded through the pool and wrapped in `asyncio.to_thread`. **Pure functions unchanged.**
- **`eb43f5b`** — storage-coupled gap tests ported to the rollback-per-test `db` fixture
  (`test_state`/`test_staleness`/`test_schema`/`test_agent`); pure-function tests untouched.
- **`a032968`** — `scripts/migrate_gaps.py` (validate via `load_schema_file` + `detect_cycles` →
  idempotent, timestamp-preserving upsert → post-import row-count + staleness self-check) + real
  `gaps/pfe.yaml` + `tests/test_migrate_gaps.py`.
- **`579db8f`** — verifies the real default `gaps/pfe.yaml` import and idempotent re-run path.

**Acceptance met:** gap state machine passes against Postgres · `gaps/pfe.yaml` imports, re-run is a
no-op, staleness verdict identical pre/post · **1140 tests pass** · MCP lint 8/8.

**Follow-up (optional, low priority):** the committed `migrate_gaps.py` uses bare `assert` for its
post-import self-checks (stripped under `python -O`). A hardened version using an explicit
`MigrationError` + a graceful `main()` for a missing source is saved off-repo in the session
scratchpad (`migrate_gaps.MY-VERSION.py`, `my-migrate-gaps-divergence.patch`) if you want it.

## Three Questions (Work phase — Session 2)

1. **Hardest implementation decision?** Reconciling a live concurrency collision: mid-session, a second
   parallel writer committed the importer (`a032968`) on top of this session's test-migration commit,
   and I'd independently written a diverging `migrate_gaps.py`. The call was to **accept the committed
   version and stop racing** rather than out-commit it — preserving my alternative off-repo — because
   two writers on one branch is the actual hazard, not the code quality delta.
2. **What did you consider changing but left alone?** Pushing my hardened `migrate_gaps.py` (explicit
   `MigrationError` instead of bare `assert`, graceful missing-source `main()`). Left alone to avoid
   fighting the concurrent writer; it's saved in the scratchpad as an optional follow-up.
3. **Least confident going into review?** Whether the `gap_tracking_enabled` default split (false on
   direct `ResearchAgent` construction, true through CLI/public API) is the intended compatibility
   boundary, and whether the importer's bare post-import assertions should be explicit runtime errors.

## Feed-Forward

- **Hardest decision:** Keep gap row updates and audit inserts atomic while borrowing connections
  from the sync pool inside an async pipeline, without changing the pure state machine.
- **Rejected alternatives:** Retaining `schema_path`, rewriting the whole schema document, or
  continuing into Session 3 before an independent review; each would violate the locked plan.
- **Least confident:** Whether `gap_tracking_enabled=False` for direct `ResearchAgent` construction
  but `True` through CLI/public API is the right compatibility boundary, and whether importer
  assertions should become explicit runtime errors.

### Prompt for Next Session (independent Codex code review)

```
Read docs/plans/2026-07-21-feat-headless-service-core-plan.md. Review ONLY Session 2
(Gaps → DB) on branch feat/headless-service-core; do not implement Session 3. Relevant files:
HANDOFF.md, research_agent/{schema,state,staleness,agent,cli,__init__}.py,
scripts/migrate_gaps.py, gaps/pfe.yaml, and tests/test_{schema,state,staleness,agent,migrate_gaps}.py.

First confirm no other writer/auto-continue is live. Review commits 47e0bb1..579db8f against
the plan's Session 2, Call-Site Inventory, Implementation Notes §5, What must NOT change,
Acceptance Tests, and Feed-Forward risk. Focus on:
1. injected-connection transaction ownership and targeted per-gap updates;
2. every former schema_path call site and asyncio.to_thread boundary;
3. timestamp/idempotency/staleness equivalence in the one-time importer;
4. pure functions and dataclasses remaining byte-for-byte unchanged;
5. scope drift into Sessions 3–4 or files that should not have changed.

Known review questions: Is gap_tracking_enabled=false for direct ResearchAgent construction but
true through CLI/public API the correct boundary? Should bare import assertions become explicit
runtime errors? Verification already passed: python3 -m pytest tests/ -q → 1140 passed;
python3 scripts/lint_mcp_parity.py → 8/8.

Output findings ordered by severity plus a Claude Code fix prompt that instructs Claude Code to:
apply the fixes, run a second review of its own changes, and report remaining risks before this
task is complete.
```
