# Brainstorm: Headless Service Core (Internal Tool — Phase A)

**Date:** 2026-07-21
**Status:** Brainstorm complete — ready for planning
**Arc:** "Robust internal tool" (research-agent → deployed web app). This is **Phase A** (backend). Phase B = quality UI; Phase C = reliability/observability.
**Prior cycle:** Cycle 33 (parking). This opens a new direction, not a resumption of the entropy roadmap.

## Prior Phase Risk

From the Cycle 33 parking brainstorm's "Least confident about":

> "Whether the Tavily key blocker will persist long enough that the novelty decomposition code goes stale. If more than 2 months pass, re-read the C30/C31 brainstorms before resuming."

**How this phase relates:** That risk has now materialized — ~2.5 months have passed. But this phase does **not** resume the entropy/novelty work; it builds infrastructure *around* the existing engine, all testable against the mocked search pipeline. So the staleness risk is **accepted and deferred**: when the entropy work is eventually resumed (a separate future cycle), the C30/C31 re-read is warranted. Nothing here touches the novelty-decomposition code.

## What We're Building

Turn the research-agent from a CLI-you-run-on-your-laptop into a **deployed internal web app for a single user (Alex)** that runs research jobs in the background and stores everything in a database.

**This phase (A) — the backend core:**
- Wrap the existing `ResearchAgent` in a **FastAPI** web service (submit job / check status / fetch report).
- A separate **worker** service that runs the long (30–180s) research jobs.
- A **Postgres database (Supabase)** replacing all file-based storage.
- Deploy both services to **Railway**.

**Designed-for now, built later:**
- Phase B — a **quality UI** (Next.js on Vercel + shadcn/ui), including a live progress bar driven by the pipeline's existing `_next_step` events.
- Phase C — observability, job retries, cost caps, "runs unwatched" hardening.

## Definition of Done (Phase A)

Phase A is **done while still parked on Tavily** — it does **not** require a live research run. Concretely:

- Both services (web + worker) deploy and stay up on Railway.
- Submitting a query via the API creates a `jobs` row; the worker claims it, runs `ResearchAgent` against **mocked search**, writes a `reports` row, and the API returns the finished report by job ID.
- Storage is fully Postgres-backed: reports, gaps, gap_audit, and critiques all read/write the DB; the gap state machine (verify / check / stale) passes its tests against the DB.
- The gap schema from `gaps/pfe.yaml` is imported into the `gaps` table.
- The CLI still runs end-to-end against the same DB.
- Existing test suite green (with new DB-backed fixtures).

**Deferred to a follow-up (gated on the Tavily key):** one real end-to-end research run through the deployed service.

## Why This Approach

The core insight: going from "a tool I run" to "a service" means **the work must outlive the request and survive restarts**. That single requirement drives every decision below. We deliberately pick the *least* complexity that delivers that robustness — no Redis, no multi-tenant, no auth — everything scoped to one user.

A pleasant surprise from the code read: the file→DB migration mostly **deletes** fragile code (filename-regex metadata parsing in `report_store.py`, the path-derived audit-log location, microsecond collision hacks). The migration is partly a cleanup, not just a plumbing swap.

## Key Decisions

| # | Decision | Choice | Why |
|---|----------|--------|-----|
| 1 | Overall scope | Quality UI wanted; sequence as **A (backend) → B (UI)** | Bundling a quality UI with the backend migration = one sprawling cycle. Design both now, build separately. |
| 2 | Job queue + topology | **Postgres-table-as-queue + separate worker** (two Railway services, no Redis) | Most robustness per unit complexity; jobs survive web redeploys; queue is "free" (same DB). Redis is YAGNI for one user. |
| 3 | Storage | **Full cutover to Postgres (Supabase)** | Files+index = two sources of truth = sync bugs. Cutover also removes fragile file code. |
| 4 | Existing data | **Migrate gaps only** | Gap schema holds stateful competitor-intel freshness; worth preserving. Old reports/critiques stay a read-only disk archive. |
| 5 | CLI fate | **Keep the CLI working against the same DB** (revisit if undesired) | Preserves the fast local dev/debug loop and a no-UI fallback; single source of truth. Cost: local runs need a `DATABASE_URL`. |
| 6 | Frontend (Phase B) | **Next.js on Vercel + shadcn/ui** | Quality path; uses existing skills/stack. |
| 7 | Build-while-parked | Build + test against **mocked search** | Tavily key still needed for real runs; all infra work is unblocked now. |

## Persisted Entities (light — schemas are a plan concern)

Rough set of what the database will hold (not table definitions yet):
- **jobs** — the queue: query, mode, status (queued/running/done/failed), timestamps, result pointer.
- **reports** — finished markdown + metadata (query, mode, gate decision, source count, created_at).
- **gaps** — the migrated gap schema (id, category, status, priority, ttl, dependency edges, timestamps).
- **gap_audit** — append-only status-flip log (replaces the `.log` file).
- **critiques** — self-critique results (replaces `reports/meta/*.yaml`).

## Scope Boundaries

**In (Phase A):** FastAPI service, worker service, Postgres cutover, gaps migration, Railway deploy, CLI kept working, mocked-search tests.

**Out (this phase):** the UI (B), auth/multi-user, billing, public exposure, cost caps, observability tooling (C).

## Known Risks / Watch-items

1. **Gap-schema code churn** — `state.py`, `staleness.py`, and the gap logic in `agent.py` (incl. the `schema_path.parent` line) all assume file paths. The migration *removes* the `schema_path.parent` fragility (audit log becomes a table) but touches this code — regression risk on the gap state machine.
2. **Job-pickup atomicity** — web inserts, worker claims. Two processes on one table need a safe claim (e.g. `SELECT … FOR UPDATE SKIP LOCKED`). Flag for the plan.
3. **Test-suite assumptions** — many tests use file paths, `datetime.now()`, and file-based fixtures; DB-backed storage needs new fixtures (a test DB or a mockable storage interface).
4. **Local dev now needs a `DATABASE_URL`** — consequence of keeping the CLI on Postgres. Mitigate with a local Postgres or a dev Supabase project.
5. **Real research still blocked on Tavily key** — infra is buildable/testable now; end-to-end live runs wait for the key.
6. **Worker must call `research_async()`, not `research()`** — `ResearchAgent.research()` wraps `asyncio.run()`, which cannot be called from inside the worker's already-running event loop. The worker path must use the existing `research_async()` entrypoint. Concrete and easy to miss.
7. **Old reports won't appear in the new list/UI** — "migrate gaps only" means the pre-existing `.md` reports remain a filesystem archive, invisible to the DB-backed report list and the Phase B UI. Confirm that's acceptable (vs. a later bulk import).

## Feed-Forward

- **Hardest decision:** Two Railway services vs. one. Chose two (separate worker) because the entire point of the phase — jobs that survive restarts — collapses if the worker dies with the web process. The added ops cost is low on Railway (same repo, different start command).
- **Rejected alternatives:** Redis/RQ (real queue, but infra + concepts unjustified for one user — YAGNI); files+DB-index hybrid (two sources of truth); one-process background task (simpler deploy, but sacrifices the robustness the phase exists to deliver).
- **Least confident:** Whether keeping the CLI on Postgres is worth the local-dev friction (needing a `DATABASE_URL`) vs. retiring the CLI or keeping a file-based dev mode. Low stakes, easily reversed.

## Three Questions

1. **Hardest decision in this session?** Sequencing the quality UI as its own phase (B) rather than cramming it into the backend cycle — respecting "one concern per cycle" against the pull to ship something visible immediately.
2. **What did you reject, and why?** Redis/RQ and the one-process topology — both lose to a Postgres-table queue + separate worker on the simplicity-vs-robustness curve for a single-user tool.
3. **Least confident going into planning?** The storage migration's blast radius on the gap-schema state machine and the test suite — the plan must inventory every file-path assumption before code starts (the same call-site audit that made past mechanical cycles review-clean).
