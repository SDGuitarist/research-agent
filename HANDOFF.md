# HANDOFF — Research Agent

**Date:** 2026-07-21
**Phase:** Work — **Session 3 COMPLETE (Reports + critiques → DB)**; next is the Codex code review of Session 3, then Session 4 (MCP parity cutover)
**Branch:** `feat/headless-service-core` (not pushed) — Session 3 in `1d9856e` (reports), `83b1d2f` (critiques); Session 2 in `47e0bb1`, `eb43f5b`, `a032968`, `579db8f` + fixes `c4370b4`, `a4dbe39`, `5eb7fbc`
**Tests:** 1170 pass · MCP lint 8/8

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

## Session 3 — Reports + critiques → DB: COMPLETE ✅

- **`1d9856e` (reports)** — `save_report(conn, ...)` inserts a report row with a stored UNIQUE
  `report_key = f"{sanitize_filename(query)}-{uuid8}"` (generated once at insert from the row's own
  uuid4; never re-derived on read). On `UniqueViolation`: retries with a fresh uuid **only** when
  `exc.diag.constraint_name` names `report_key` (3-attempt cap → `StateError`); a `job_id` conflict
  raises immediately (one-report-per-job invariant, S6's concern). `get_reports(conn)` reads the DB
  (`ReportInfo.filename` now carries the key, `query_name` the raw query). CLI: `--list` reads DB
  rows (`date  query  [key]`); standard/deep auto-save writes ONE DB row and **no file**; explicit
  `-o` still writes a file; `--open` without `-o` warns. All DB errors wrap to `StateError`
  (⊂ `ResearchError`, so CLI error handling catches them); `--list`/`--critique-history` fail fast
  with the clear ConfigError message when `DATABASE_URL` is missing.
- **`83b1d2f` (critiques)** — `save_critique(conn, result) -> id` inserts a critiques row
  (weaknesses/suggestions pass `sanitize_content` on write — idempotent since C27, so the read-side
  sanitize in `_summarize_patterns` can't double-encode). `load_critique_history(conn, limit=10)`
  mirrors the file semantics exactly: newest `limit` rows regardless of pass, filter passing,
  require ≥3 — recent failures push older passes out of the window (pinned by test).
  `agent.py`: `_run_critique` saves via the pool (catches `OSError|ConfigError|StateError` — never
  crashes the pipeline); `_load_critique_history_db()` degrades to no-history on
  `ConfigError|StateError` (optional enhancement; also keeps the ~970 mock-only pipeline tests off
  the DB). CLI `--critique`/`--critique-history` use the DB.
- **MCP server: 4 behavior-preserving shim lines only** (NOT the S4 cutover): `list_saved_reports`
  → `get_archived_reports()` (renamed file glob), `critique_report` → `save_critique_file`,
  `get_critique_history` → `load_critique_history_files`. MCP runtime behavior is byte-identical
  (still file-based); the legacy trio is commented for deletion in S4.
- **Tests** — storage-coupled tests moved to the rollback-per-test `db` fixture: `save_report`
  round-trip/format, same-query-twice → 2 rows distinct keys (EARS), collision-retry (distinct
  uuids sharing the 8-hex prefix — forcing the *same* uuid collides on `reports_pkey` instead,
  which is exactly why the constraint-name check exists), retry-exhaustion, job_id-conflict
  no-retry; CLI end-to-end `main()` runs proving 1 DB row + no `reports/` dir; critique row
  round-trip incl. sanitize-on-write; DB history window/limit/degradation. Legacy file readers
  keep their old tests under the renamed functions (die with them in S4).

**Acceptance met:** CLI `--list` reads DB rows · a CLI run writes ONE report row and no file ·
identical query twice → two rows, distinct keys · 1170 tests pass · MCP lint 8/8.

## Three Questions (Work phase — Session 3)

1. **Hardest implementation decision?** The MCP-server interim: S3 changes the signatures of
   `get_reports`/`save_critique`/`load_critique_history`, but the MCP cutover is locked to S4.
   Leaving `mcp_server.py` textually untouched would have left three tools runtime-broken (mocked
   tests would still pass — worse, silently). Chose to keep the legacy file functions alive under
   explicit `*_file`/`archived` names and repoint MCP's imports (4 lines, zero behavior change),
   accepting a technical violation of "don't touch mcp_server.py" to honor the deeper guardrail
   ("the MCP tool contract must not change").
2. **What did you consider changing but left alone?** (a) Sanitizing `reports.query`/`content` on
   write — the guardrail says "sanitize_content on every DB write path", but escaping the report
   markdown would corrupt round-trips and violate "same reports for same inputs"; followed the S2
   precedent (verbatim storage + parameterized SQL + sanitize at prompt-consumption boundaries)
   and applied write-time sanitization only to the critique free-text fields, where it's idempotent
   with the existing read-side sanitize. **Flagged for the reviewer.** (b) Catching
   `psycopg_pool.PoolTimeout` in `_load_critique_history_db` — left out to stay consistent with the
   gap path, which also lets pool timeouts propagate.
3. **Least confident going into review?** The critique-history degradation contract: history now
   silently degrades to "no guidance" on `ConfigError`/`StateError` (warning-logged). Right for an
   optional enhancement and required to keep ~970 no-DB tests green, but it means a misconfigured
   deploy loses adaptive prompts *and* per-run critique rows with only log lines as evidence.

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

- **Hardest decision:** The S3↔S4 seam — cutting the canonical function names over to the DB
  while keeping the MCP server's file-based behavior byte-identical via explicitly-named legacy
  shims, instead of leaving MCP runtime-broken behind green mocked tests.
- **Rejected alternatives:** Giving the DB functions temporary non-plan names (S4 rename churn);
  cutting MCP over to the DB early (locked to S4); sanitizing report content on DB write (corrupts
  round-trips; violates "same reports for same inputs").
- **Least confident:** The silent-degradation contract for critique history/save when the DB is
  unavailable (warning-logged, pipeline continues) — right locally, but a deploy misconfig loses
  critique data quietly.

### Prompt for Next Session (Codex — review Session 3)

```
Review Session 3 (Reports + critiques → Postgres) on branch feat/headless-service-core:
commits 1d9856e and 83b1d2f (diff base: 713d2a5). Plan:
docs/plans/2026-07-21-feat-headless-service-core-plan.md — sections "Report identity &
report_key", "Call-Site Inventory", "What must NOT change", EARS. Context: storage functions
take an INJECTED conn (caller owns the transaction; nested `with conn.transaction():` =
savepoint; never conn.commit() inside). Tests: python3 -m pytest tests/ -q (1170 pass,
real Postgres via testcontainers); MCP lint: python3 scripts/lint_mcp_parity.py.

Scrutinize specifically:
1. save_report's UniqueViolation handling — the constraint_name check ("report_key" in name)
   that separates retryable key collisions from job_id invariant breaches; the 3-attempt cap;
   savepoint rollback semantics under the rollback-per-test fixture.
2. Sanitization decision (FLAGGED): reports.query/content are stored VERBATIM (parameterized
   SQL; sanitize_content stays at prompt-consumption boundaries, per S2 precedent) while
   critique weaknesses/suggestions ARE sanitized on write (idempotent with the read-side
   sanitize). Is the verbatim choice defensible for every future consumer (S5 web UI renders
   these fields)?
3. load_critique_history(conn) window semantics — newest LIMIT rows then filter passing —
   exact parity with the legacy file reader? Any drift in the ≥3-passing gate?
4. Degradation contract: _load_critique_history_db and _run_critique swallow
   ConfigError/StateError (warning only). Acceptable for an optional enhancement, or should
   a worker/deploy context escalate?
5. MCP interim shims (4 lines in mcp_server.py): list_saved_reports→get_archived_reports,
   critique_report→save_critique_file, get_critique_history→load_critique_history_files —
   confirm MCP behavior is byte-identical and nothing else drifted into the S4 scope.
6. CLI: --list/--critique-history fail-fast paths; auto-save block ordering (-o vs DB vs
   --open warnings); StateError ⊂ ResearchError error flow.
Return P0/P1/P2 findings.
```

### Prompt for the Session After Review (Claude Code — apply fixes, then Session 4)

```
FIRST: confirm no other session / auto-continue is live on this branch — run
`git log --oneline -3` and `git status --short`. Expect HEAD 83b1d2f (or the HANDOFF-update
commit directly on top of it) and a clean worktree before writing anything.

Read HANDOFF.md (Session 3 section + Three Questions) and the Codex review findings. Apply the
review fixes for Session 3 in small commits, re-run python3 -m pytest tests/ -q and
python3 scripts/lint_mcp_parity.py, update HANDOFF, and STOP. Do NOT start Session 4 in the
same session as the fixes.
```

Session 1 review residuals (still open, none block S4): disposable-DB guard is convention-based;
open_pool doesn't close a half-open pool on failure (latent until S5–6).
