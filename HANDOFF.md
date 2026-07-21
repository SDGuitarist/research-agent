# HANDOFF — Research Agent

**Date:** 2026-07-21
**Phase:** Work — **Session 2 COMPLETE + review fixes applied & second-reviewed**; next is Session 3 (Reports + critiques → DB)
**Branch:** `feat/headless-service-core` (not pushed) — Session 2 in `47e0bb1`, `eb43f5b`, `a032968`, `579db8f`; review fixes in `c4370b4`, `a4dbe39`, `5eb7fbc`

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

## Session 2 Review Fixes (Codex review → applied → second-reviewed) ✅

Codex's independent review returned 3 findings; all applied and self-reviewed:

- **`5eb7fbc` (fix 1)** — profile-driven gap-tracking activation restored: `gap_tracking_enabled`
  is now a tri-state override (`None` = auto → on only when the effective context's profile
  declares `gap_schema`; `True`/`False` force). CLI + `run_research_async` stop forcing it.
  New `_gap_tracking_active()` guards the pre-research check and all 3 post-research sites —
  unrelated queries can never be short-circuited by global gap rows. +8 tests (boundary units,
  pipeline activation both ways, public-API construction).
- **`c4370b4` (fix 2)** — importer self-checks hardened: bare `assert` → explicit `MigrationError`
  (survives `python -O`, rolls the import transaction back); staleness equivalence now verified
  for EVERY imported gap; injectable `now` for deterministic tests. (This supersedes the
  scratchpad follow-up — the hardened version is now in-tree.)
- **`a4dbe39` (fix 3)** — save-failure test proves atomicity: after a real `log_flip` insert and a
  failing `save_schema` in one transaction, no `gap_audit` row persists and the gap row is unchanged.

**Second review (against plan / Call-Site Inventory / What must NOT change):** pure functions +
dataclasses byte-for-byte identical (`git diff` empty on state/staleness/schema); all 4
`asyncio.to_thread` boundaries intact; injected-conn/caller-owns-txn preserved; no S3/S4 drift.
**1148 tests pass · MCP lint 8/8.**

**Remaining risks (reported, accepted):**
1. `migrate_gaps.main()` surfaces `SchemaError`/`MigrationError` as a traceback (exit ≠ 0,
   rollback still guaranteed) — graceful CLI messaging deliberately left out of the fix scope.
2. `profile.gap_schema` is now purely declarative (the old file-existence check is gone — the DB
   is the store). A gap-declaring context over an empty `gaps` table proceeds as a normal query.
3. If a context fails to load (FAILED status), auto mode leaves tracking off for that run —
   mirrors the pre-S2 behavior when the profile was unavailable.

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

### Prompt for Next Session (Claude Code — implement Session 3)

```
FIRST: confirm no other session / auto-continue is live on this branch — run
`git log --oneline -3` and `git status --short`. Expect HEAD 5eb7fbc (or the HANDOFF-update
commit directly on top of it) and a clean worktree before writing anything.

Read docs/plans/2026-07-21-feat-headless-service-core-plan.md — specifically "Implementation
Phases (Sessions)" → Session 3, the "Call-Site Inventory", the "Report identity & report_key"
section, and "What must NOT change" + "Acceptance Tests (EARS)". Also skim HANDOFF.md.

We are on branch feat/headless-service-core (nothing pushed). Sessions 1–2 are DONE, reviewed,
and review-fixed — 1148 tests pass; MCP lint 8/8. The DB foundation (config.py, db.py pool with
INJECTED conn, migrate.py, migrations/001_init.sql with the reports + critiques tables ALREADY
EXISTING) and the gap cutover are in place. Storage functions take an INJECTED conn; caller owns
the transaction (never conn.commit() inside — use `with conn.transaction():`). conftest gives you
db (rollback-per-test injected conn) and committed_db (TRUNCATE). Test cmd: python3 -m pytest tests/ -q.

Implement ONLY Session 3 (Reports + critiques → DB) — then commit and stop. Do NOT proceed to S4.

Session 3 scope:
1. report_store.get_reports → DB query (injected conn). save_report(conn, ...) replaces
   get_auto_save_path + atomic_write; generate report_key = f"{sanitize_filename(query)[:50]}-{uuid8}"
   as a stored UNIQUE column (never re-derived on read); regenerate + retry on UniqueViolation.
2. load_critique_history: glob+parse → SQL query (min 3). save_critique → DB insert (injected conn).
3. Update cli.py (--list, auto-save path, --critique-history) and agent.py:222/445 to the new
   signatures. Old reports/ + reports/meta/ files become a read-only disk archive (do NOT migrate them).
4. Migrate storage-coupled tests (test_report_store, test_critique/critique-history, cli assertions)
   to the db fixture; keep pure/format tests on mocks.

Acceptance: CLI --list reads report rows from the DB; a CLI run writes ONE report row (report_key
UNIQUE) and NOT a file under reports/; identical query submitted twice → two rows, distinct
report_keys; full suite green; MCP lint 8/8 (python3 scripts/lint_mcp_parity.py).

Guardrails: don't touch the MCP server report/key cutover (S4) or web/worker (S5–6); reuse
sanitize_content on every DB write path; don't edit 001_init.sql (add 002_*.sql only if truly
needed); follow "What must NOT change"; SMALL COMMITS, one writer per branch. After committing
Session 3, stop, update HANDOFF with the Codex code-review baton, and say DONE. Do NOT proceed
to Session 4.

Session 1 review residuals (still open, none block S3): disposable-DB guard is convention-based;
open_pool doesn't close a half-open pool on failure (latent until S5–6).
```
