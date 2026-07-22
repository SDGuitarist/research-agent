# HANDOFF — Research Agent

**Date:** 2026-07-21
**Phase:** Work — **Session 5 COMPLETE**; next is independent Session 5 code review
**Branch:** `feat/headless-service-core` — Session 5 in `d248462`; Session 4 reviewed clean in `ffea869`
**Tests:** 1177 pass · MCP lint 8/8 + Postgres storage parity for CLI/MCP/web

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

## Session 4 — MCP parity cutover: COMPLETE ✅

- **`dc0e495`** moves every MCP storage path to Postgres. Standard/deep `run_research`
  auto-save uses `save_report` in `asyncio.to_thread`; `list_saved_reports` uses
  `get_reports`; `get_report`, `critique_report`, and `generate_followups` load verbatim
  content by canonical `report_key`; critique results save with `save_critique`; and
  `get_critique_history` uses the DB history window.
- All borrows go through `db.pooled_connection()`. Connections are released before the
  Anthropic critique/follow-up calls, then a fresh short borrow persists the critique.
  `ConfigError` and `StateError` become MCP `ToolError`; DB internals are not exposed.
- `_validate_report_filename` is replaced by `_validate_report_key` with the planned
  `[a-zA-Z0-9_-]+` contract. The MCP parameter names are now `report_key`, while all
  identifiers remain strings and all 8 tool names remain unchanged.
- Removed the three Session 3 bridge shims (`get_archived_reports`, `save_critique_file`,
  `load_critique_history_files`) and their archive-only tests. Added the injected-connection
  `report_store.get_report(conn, report_key)` and a storage-neutral
  `critique_report_text(...)` so CLI file critique remains supported without MCP temp files.
- Extended `scripts/lint_mcp_parity.py` to verify that active CLI/MCP consumers both import
  **and call** their required shared Postgres operations and do not import removed file shims.
  The declared web checks activate automatically when Session 5 adds `research_agent/web.py`.

**Acceptance met:** all 8 MCP tools retain their names and use DB storage where applicable;
report lookup is by canonical key; no interim file shim remains; `StateError`/`ConfigError`
translate to `ToolError`; **1168 tests pass** against real Postgres; parity lint green.

### Feed-Forward (Session 4)

- **Hardest decision:** keeping database borrows short around `critique_report` and
  `generate_followups`. The report is loaded and the connection released before the external
  Anthropic call; critique persistence gets a separate borrow. This avoids holding a scarce
  pool slot through a 30-second network call.
- **Rejected alternatives:** direct SQL inside `mcp_server.py` (would bypass the injected-conn
  storage contract); holding one connection across load/API/save (pool starvation risk);
  leaving MCP auto-save on disk (two sources of truth); making the lint require a nonexistent
  `web.py` immediately (would make Session 4 acceptance impossible).
- **Least confident:** the phase-aware parity lint proves required storage functions are
  imported and called, but it cannot prove semantic argument parity. Session 5 must activate
  the web checks and its integration tests must verify verbatim-at-rest/render-safe behavior.

### Session 4 Review (Claude Code, independent) — CLEAN ✅

Second-agent review of `dc0e495` against `a18107f`: **no P0/P1/P2 findings**, no edits made.
Independently re-ran the suite (**1168 pass**) and `lint_mcp_parity.py` (8/8 + cli/mcp storage
parity). Verified: `_validate_report_key` (empty/null-byte/>255/charset → rejects `../`, `\`,
spaces); caller-owned transactions with **no `conn.commit()`** and the connection **released
before every Anthropic call** (load → release → API → fresh borrow to save); `asyncio.to_thread`
only around sync DB work; safe `StateError`/`ConfigError` → `ToolError` mapping incl. not-found;
autosave field parity with the CLI (`gate_decision=result.status` is the gate decision);
`critique_report_file` delegates to `critique_report_text` verbatim (CLI `--critique` unchanged);
zero dangling refs to the deleted shims; all 8 tool names intact; S3 P1/P2 fixes still in place;
no scope drift into S5/6 (the `web` lint entry is inert until `web.py` exists).

Accepted risks (non-blocking): (1) `run_research` autosave failure discards the just-generated
report — consistent with CLI fail-fast, revisit UX in S5; (2) the parity lint proves import+call,
not argument semantics — S5 web integration tests must assert verbatim-at-rest/render-safe;
(3) pre-existing (not S4): `report_store.get_auto_save_path` is now dead production code
(tests-only) since S3 moved auto-save to the DB — candidate for a future cleanup.

## Session 5 — FastAPI web service: COMPLETE ✅

- **`d248462`** adds `research_agent/web.py` with plain synchronous FastAPI routes, an
  application lifespan that opens/closes the shared pool on `app.state`, and an injected
  `get_conn` yield dependency backed by `db.pooled_connection()`.
- `POST /research` validates with `check_query_vagueness` before connection checkout, inserts
  a `queued` job, and returns 202 with its UUID and `Location`. Job lookup uses a UUID path
  type (malformed → 422), returns 404 for unknown IDs, status-only payloads while queued or
  running, failure error text for failed jobs, and report key/content for done jobs.
- Report list/detail routes reuse `get_reports`/`get_report` and expose canonical
  `report_key`; `/health` is DB-free liveness, `/health/ready` executes `SELECT 1`, and
  `/modes` reuses the public `list_modes()` function.
- Central handlers map vague queries → 400, missing resources → 404, and
  `OperationalError`/`PoolTimeout`/`StateError`/`ConfigError` → a non-leaking 503 response.
- The service has JSON routes only. Query/content/error stay byte-identical at rest and are
  returned as `application/json` data; no HTML or Markdown renderer exists in Session 5.
- Added the `research-agent-web` entry point and 9 TestClient integration tests against the
  rollback-isolated real Postgres fixture. Adding `web.py` activated the existing parity-lint
  web checks.

**Acceptance met:** valid POST → queued UUID + Location; vague → 400 and no row; unknown job
→ 404; malformed UUID → 422; DB failure → 503; verbatim script-like query/content stays
unchanged in Postgres and is returned only as non-executable JSON; **1177 tests pass**;
parity lint checks CLI/MCP/web.

### Feed-Forward (Session 5)

- **Hardest decision:** guaranteeing vague-query validation happens before the database is
  borrowed while retaining FastAPI dependency injection. The request validation is its own
  dependency and appears before `get_conn`; a DB-down test pins vague → 400 before checkout.
- **Rejected alternatives:** `async def` routes around sync psycopg (would block the event
  loop); direct connection management in every route (duplicates lifecycle/error behavior);
  an HTML/Markdown view (creates a sanitizer surface Phase A does not need); a new job
  repository abstraction before Session 6 defines the queue operations.
- **Least confident:** JSON `application/json` makes verbatim `<script>` strings data rather
  than executable markup, as the plan requires, but it intentionally does not mutate or
  HTML-entity-escape the returned string. The independent review should verify that this
  boundary remains safe for the intended browser consumer and that no content-sniffing or
  future interpolation assumption requires an additional response header.

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

## Session 3 Review Fixes — applied ✅ (P1, P2)

Two findings from the Session 3 review, fixed against diff base `713d2a5`. No S4+ scope
touched: `mcp_server.py` byte-identical, gap paths (S2) unchanged, all 8 MCP tools still
file-based via the interim shims.

- **`a3e04af` (P1 — DB error boundary).** `load_critique_history` swallowed every psycopg
  error into `NOT_CONFIGURED`, so CLI `--critique-history` read a broken query/schema/
  connection as *healthy empty* and exited 0. And pool-boundary failures
  (`psycopg_pool.PoolTimeout`, a `psycopg.OperationalError` subclass — **not** a
  `ResearchError`) leaked raw out of `--list`, `--critique-history`, CLI auto-save,
  `_load_critique_history_db`, and `_run_critique`.
  - New `db.pooled_connection()` — the single pool-boundary that wraps
    PoolTimeout/connection failures in `StateError`; `ConfigError` (missing `DATABASE_URL`)
    still propagates unchanged (both ⊂ `ResearchError`).
  - `load_critique_history` now **raises** `StateError` on DB failure; `NOT_CONFIGURED`
    means only "healthy: fewer than 3 passing critiques".
  - CLI critique/report/list paths + agent critique paths borrow via `pooled_connection()`.
    **Context split preserved:** direct CLI ops fail fast (nonzero exit, clear error);
    `ResearchAgent` critique history/persistence stay optional and degrade with a warning.
  - Tests: `pooled_connection` normalization + ConfigError passthrough; CLI fail-fast on
    missing-config / pool-timeout / SQL failure; agent degradation on all three.

- **`30594e3` (P2 — critique-history validation parity).** The DB loader only rejected
  failing rows or NULL dimensions; the legacy file reader also rejected non-integer/
  out-of-range scores and non-string/over-200-char weaknesses/suggestions before the
  ≥3-passing gate. `load_critique_history` now validates each selected row with the file
  reader's own predicate (`_validate_critique_yaml`) — `suggestions` added to the SELECT
  for full parity — **on the newest-LIMIT window** (kept newest-LIMIT-first-then-filter),
  so an invalid row inside the window can't be replaced by an older valid row outside it.
  Real-Postgres tests: out-of-range score / over-length weaknesses / over-length
  suggestions / NULL dimension inside the window don't count; 3 valid passing still load.

- **P2 feed-forward (plan updated).** The plan's blanket "sanitize on every DB write path"
  wording now documents the **intentional exception**: `reports.query`/`content` are stored
  **verbatim** (parameterized SQL is the injection defense; `sanitize_content` is a
  prompt-boundary escaper, not a web/JSON-render sanitizer). An explicit **Session 5
  requirement + acceptance test** was added: the web/JSON layer must escape/sanitize
  untrusted `query`/`content`/`error` at the render boundary. Not implemented here.

**Self-review (second pass, against S3 scope / txn ownership / CLI error paths / MCP
byte-parity / plan):** clean. `pooled_connection` never opens a transaction or commits —
storage functions still own `with conn.transaction()`; caller-owns-txn intact. Only 8
files changed (4 modules + 4 test files). **1188 tests pass · MCP lint 8/8.**

**Residual risk (accepted):** `pooled_connection` wraps the whole borrow (including
connection *return*), so the astronomically-rare "operation committed, then the pool
connection-return fails" path surfaces as a `StateError` after a successful write — a
false error, not corruption (a CLI re-run mints a distinct `report_key`). This is a strict
improvement over the pre-fix raw leak, and correctly treats a connection-return failure as
a connection failure per the fix's contract.

## Three Questions (Fix session — Session 3 review fixes)

1. **Hardest fix in this batch?** Deciding *where* to normalize pool errors. `PoolTimeout`
   is actually a `psycopg.Error` subclass, so it's tempting to lean on the storage
   functions' existing `except PsycopgError` — but those never see it, because the timeout
   fires at pool checkout, *outside* the storage call. The right boundary is a single
   `pooled_connection()` context manager at the borrow site, wrapping checkout/open failures
   in `StateError` while letting `ConfigError` and the storage functions' own `StateError`
   pass through untouched. This keeps the CLI-fails-fast / agent-degrades split working with
   each caller's *existing* `except` clauses — no per-site error handling.
2. **What did you consider fixing differently, and why didn't you?** For P2, enforcing the
   invariants with a DB `CHECK` constraint (write/schema side) instead of read-side
   validation. Rejected: a constraint can't reject rows already in the table, and the review
   explicitly wanted "invalid rows *inside the newest window* don't count" — a read-time
   property. Reusing the file reader's exact predicate (`_validate_critique_yaml`) also
   guarantees parity by construction rather than by a hand-copied second rule set. Also
   considered routing the gap paths through `pooled_connection` for uniformity — left alone
   (S2 scope; the gap path intentionally lets PoolTimeout propagate).
3. **Least confident going into the next phase (Session 4)?** That `pooled_connection` is
   the seam Session 4's MCP cutover will also want. S4 moves MCP off the file shims onto the
   DB storage functions; those calls should borrow through `pooled_connection()` too, and
   MCP's `ToolError` translation must map `StateError`/`ConfigError` the way the CLI maps
   them to exit codes — a parity point the extended parity lint should assert.

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

> Session 4 review is DONE and the Session 5 implementation below has been consumed.

### Consumed Prompt (Session 5 — FastAPI web service)

```
Work in /Users/alejandroguillen/Projects/research-agent
Branch: feat/headless-service-core · HEAD ffea869

FIRST: confirm no other session / auto-continue is live on this branch — run
`git log --oneline -3` and `git status --short`. Expect HEAD ffea869 (or a HANDOFF/docs
commit directly on top of it) and a clean worktree before writing anything. Session 4 is
reviewed-clean; do only Session 5.

Read docs/plans/2026-07-21-feat-headless-service-core-plan.md — "Session 5 — FastAPI web
service", Implementation Notes §4 (FastAPI), the "Session 5 requirement (render-boundary
escaping)" block under "What must NOT change", and EARS — plus HANDOFF.md (Session 4 +
Session 4 Review). Relevant files: research_agent/web.py (new), research_agent/db.py
(pooled_connection + lifespan pool open/close), research_agent/report_store.py (get_reports,
get_report), research_agent/query_validation.py (check_query_vagueness),
research_agent/modes.py (list_modes), tests/conftest.py (db/committed_db fixtures),
scripts/lint_mcp_parity.py (web checks activate once web.py exists).

Implement Session 5: create research_agent/web.py (FastAPI; plain `def` routes so FastAPI
threadpools them → call sync storage directly; lifespan opens/closes the pool on app.state;
a get_conn yield-dependency borrows via db.pooled_connection()):
- POST /research → validate with check_query_vagueness at POST (vague → 400, no job created);
  insert a queued jobs row; return 202 + job UUID (+ Location header).
- GET /jobs/{id:uuid} → auto-422 on malformed uuid / 404 unknown / running → status only /
  done → status + report content.
- GET /reports (list) and GET /reports/{key} (404 unknown).
- GET /health → liveness only, NO DB ping; GET /health/ready → pings DB.
- GET /modes → reuse list_modes() (not the MCP tool).
- Central exception handlers: VagueQueryError → 400, not-found → 404,
  OperationalError/PoolTimeout (and StateError/ConfigError) → 503.
- RENDER-BOUNDARY ESCAPING (S3 P2 feed-forward): query/content/error are stored VERBATIM; the
  web layer does the escaping. Return them as JSON (application/json, no HTML interpolation);
  if any HTML/Markdown view exists, HTML-escape query/error and render report Markdown through
  a sanitizing renderer (no raw HTML passthrough).
- Add the research-agent-web entry point to pyproject.

Acceptance (TestClient vs a test DB): POST valid → 202 + queued job UUID; vague → 400, no job;
GET unknown job → 404; malformed uuid → 422; DB down → 503; a query containing
`<script>alert(1)</script>` is stored byte-identical (verbatim at rest) and returned
escaped/non-executable, never as live markup. Extend scripts/lint_mcp_parity.py's web checks.
Run python3 -m pytest tests/ -q and python3 scripts/lint_mcp_parity.py. Do only Session 5 —
commit and stop.
```

Session 1 review residuals (still open, none block S5): disposable-DB guard is convention-based;
open_pool doesn't close a half-open pool on failure (latent until S5–6).

### Prompt for Next Session (Session 5 — independent code review)

```
Work in /Users/alejandroguillen/Projects/research-agent
Branch: feat/headless-service-core
Expected live HEAD: d248462, or a HANDOFF/docs-only commit directly on top of it.

FIRST: confirm the branch is settled by running `git log --oneline -3` and
`git status --short`. Expect implementation commit d248462 and a clean worktree. A running
Claude or Codex process is not evidence of another writer; block only if HEAD moved
unexpectedly or the worktree is dirty.

Perform a read-only independent code review of Session 5. Review commit d248462 against diff
base a9cb47c. Do not edit files, implement fixes, commit, or begin Session 6.

Read docs/plans/2026-07-21-feat-headless-service-core-plan.md — Session 5, Implementation
Notes §4, the render-boundary escaping requirement under What must NOT change, and EARS —
plus HANDOFF.md Session 4 Review and Session 5.

The Session 5 implementation changed only research_agent/web.py, pyproject.toml, and
tests/test_web.py. Scrutinize:
1. POST /research validates vagueness before borrowing a connection or inserting a row.
2. Lifespan pool ownership on app.state, the pooled_connection-backed get_conn yield
   dependency, caller-owned transactions, and plain def database routes.
3. Vague → 400, missing → 404, malformed UUID → 422, and DB/config/pool failures → a
   non-leaking 503.
4. Query/content/error remain verbatim at rest and are returned only as application/json
   data. Verify script-like strings cannot execute and no HTML/Markdown renderer exists.
5. Exact status-dependent job payloads, canonical report_key behavior, report list/detail,
   DB-free /health, DB-pinging /health/ready, and reuse of the public list_modes() function
   rather than the MCP tool.
6. Adding web.py actually activates useful CLI/MCP/web storage checks in
   scripts/lint_mcp_parity.py, including its known import+call semantic blind spot.
7. The research-agent-web entry point, test coverage, pool cleanup, and any scope drift into
   Session 6.

You may run python3 -m pytest tests/ -q and python3 scripts/lint_mcp_parity.py. Return P0/P1/P2
findings only, ordered by severity, with exact file and line references and concise impact. If
clean, say so and identify remaining verification risk. Do not implement anything.
```
