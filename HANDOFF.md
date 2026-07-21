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
- **Session 1 (Foundations): DONE** (commit `3a379c0`). Files: `config.py`, `db.py`, `migrate.py`, `migrations/001_init.sql`, `errors.py` (+`ConfigError`), `tests/conftest.py` (opt-in Postgres fixtures), `tests/test_{config,migrate,db}.py`. Deps added: `psycopg[binary,pool]`, `testcontainers[postgres]` (fastapi/uvicorn already present). **1134 tests pass; MCP lint 8/8.** DB tests run against a real Postgres via testcontainers (Docker).

## Next: Session 2 — Gaps → DB (prove the state machine first; `verify_first`)

Rewrite `load_schema`/`save_schema`/`log_flip` to Postgres (per-gap rows), keep the pure functions (`mark_verified`/`mark_checked`/`detect_stale`/`select_batch`/`_parse_gap`) untouched, update `agent.py` (drop `schema_path`/`schema_path.parent`), and add `scripts/migrate_gaps.py` (idempotent, timestamp-preserving, post-import equality assertion). Storage functions take an **injected `conn`**.

## Three Questions (Work phase — Session 1)

1. **Hardest implementation decision?** Getting the rollback-per-test fixture right: the constraint tests initially left the transaction aborted (`InFailedSqlTransaction`) because `pytest.raises` was *inside* the savepoint. Fix: wrap the savepoint *with* `pytest.raises` so the error rolls the savepoint back and the outer fixture transaction survives. Also chose partial indexes over the composite queue index (per Impl. Notes §1).
2. **What did you consider changing but left alone?** Ripping out the scattered `os.environ.get`/`load_dotenv` sites to route everything through `config.py` now — left alone to keep Session 1 additive and non-breaking; that migration happens when the CLI/web/worker wire it in (Sessions 5–7). The existing `report_store`/`state` file code is likewise untouched (Sessions 2–3 migrate it).
3. **Least confident going into Session 2?** Whether the injected-`conn` rewrite of the gap I/O cleanly accommodates `agent.py`'s gap logic once `schema_path` disappears (the flagged blast radius), and whether `migrate.py`'s multi-statement `execute()` stays robust for a future migration containing dollar-quoted function bodies (worked fine for pure DDL).

### Prompt for Next Session

```
Read docs/plans/2026-07-21-feat-headless-service-core-plan.md (Session 2 + "Call-Site
Inventory" + Impl. Notes §5). Implement ONLY Session 2 (Gaps → DB): rewrite load_schema/
save_schema/log_flip to Postgres per-gap rows with an injected conn, keep the pure gap
functions untouched, update agent.py to drop schema_path, add scripts/migrate_gaps.py
(idempotent + timestamp-preserving + equality assertion), migrate the gap storage tests to
the db fixtures. Do ONLY Session 2 — commit and stop. Prove the gap state machine against
Postgres before wiring anything else. After committing, stop and say DONE.
```
