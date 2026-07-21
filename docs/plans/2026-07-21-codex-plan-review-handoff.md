# Codex Plan Review — Headless Service Core (Phase A)

You are doing an **external plan review** (fresh context, before any code is written) for a compound-engineering workflow. Be adversarial and specific. This is a **single-user internal tool** — flag over-engineering (YAGNI) as readily as under-engineering.

## Repo & plan
- Repo: `research-agent` (Python 3.10+, a CLI + MCP web-research agent; ~8.8k LOC, 1,119 tests).
- **Plan to review:** `docs/plans/2026-07-21-feat-headless-service-core-plan.md`
- Origin brainstorm: `docs/brainstorms/2026-07-21-headless-service-core-brainstorm.md`

## What Phase A builds
Turn the CLI into a deployed internal web service: a FastAPI app enqueues a research job into a Postgres `jobs` table; a separate worker claims it (`SELECT FOR UPDATE SKIP LOCKED`), runs the existing `ResearchAgent` (30–180s) against **mocked search**, writes a report, marks the job done. All file-based **state** (reports, gaps, gap_audit, critiques) migrates to Postgres (Supabase); `contexts/*.md` stay as files. CLI + MCP + web share one storage layer. Two services deploy to Railway. **Out of scope:** auth, billing, UI, cost caps.

## Read first
- The plan in full — especially "Implementation Notes (deepened research)", "Call-Site Inventory", and "Acceptance Tests (EARS)".
- Verify the plan's claims against source: `research_agent/agent.py` (gap logic ~155–228, 393–529, 808–975), `state.py`, `staleness.py`, `schema.py`, `report_store.py`, `critique.py`, `context.py:582-650`, `cli.py`, `mcp_server.py`, `__init__.py`, `tests/conftest.py`.

## Scrutinize specifically (return P0/P1/P2 with file:line or plan-section refs)
1. **Transaction boundaries & reaper.** Short claim txn → run outside txn → atomic finish (`INSERT ... ON CONFLICT (job_id) DO NOTHING` + `UPDATE ... WHERE claim_id=$mine AND status='running'`). Heartbeat-decoupled lease (~90s, must exceed heartbeat interval). Any window for lost, duplicated, or stuck jobs? Is `claim_id` + `UNIQUE(job_id)` actually sufficient against a reaper/worker race?
2. **The sync-storage design (decision #3, author confidence ~75%).** Sync psycopg3 storage; a sync worker loop calling `asyncio.run(research_async())` per job; async FastAPI with plain `def` routes (threadpooled) touching only the DB. Is the event-loop-trap reasoning sound? Are the 4 in-pipeline sync storage calls (`agent.py:501,842,883,973`) safe under this model at single-user scale, or a latent hazard? Would fully-async storage be materially better, or is this the right call?
3. **Storage-injects-`conn` refactor.** The plan changes storage signatures to take a `conn`. Trace the blast radius across `agent.py`'s gap-state calls, the CLI, and the MCP server — does anything break the "gap state machine is pure and untouched" claim?
4. **Gaps whole-doc → per-row + migration.** The migration must be idempotent, preserve original UTC timestamps, and not regress staleness math. Is upsert + a post-import equality assertion sufficient? Any concurrency hazard now that two writers can update different gaps?
5. **Cross-consumer parity (CLI/MCP/web).** Every storage op reachable and identically sanitized from all three; the plan extends `scripts/lint_mcp_parity.py`. Is any op reachable from one entry point but not the others? Is `sanitize_content` on every write path?
6. **Pooler-mode decision.** Plan uses Supabase **session pooler (5432)** for app + worker + migrations (a resolved cross-agent conflict). Sound for a single-user tool, or should the app be on transaction mode (6543)?
7. **EARS testability.** Are any acceptance criteria (especially the crash/concurrency ones) untestable without a real Postgres + fault injection? Is the mock seam (search stubbed; Claude live for the DoD smoke test) coherent?
8. **Scope / YAGNI.** Is anything over-built for one user (the reaper, pg_cron, testcontainers)? Anything under-specified that will block Session 1?

## Return format
Prioritized findings — **P0** (blocks a correct/shippable service), **P1** (silent corruption or bad UX), **P2** (specify / nice-to-have) — each with the file or plan section it references and a one-line suggested fix. Call out explicitly if any author-flagged confidence decision is wrong: #3 sync-storage model (~75%), minimal-reaper-in-Phase-A (~80%), mock seam (~85%).
