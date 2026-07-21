# HANDOFF — Research Agent

**Date:** 2026-07-21
**Phase:** Plan Review (external Codex review pending)
**Branch:** `main` (no feature branch yet — Work hasn't started)

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

## Next phase: Plan Review (Codex)

1. Paste the clipboard handoff into Codex (fresh context).
2. Bring Codex's P0/P1/P2 findings back here.
3. Fold the valid ones into the plan (note any rejected + why).
4. Then `/workflows:work` **Session 1 (Foundations)**.

## Three Questions (Plan phase)

Full answers in the plan's "Three Questions (Plan phase)" section. **Least confident going into work:** Session 2's blast radius on `agent.py`'s gap logic once `schema_path` disappears — hence `verify_first: true` and gaps-first sequencing. The other flagged uncertainty is decision #3 (sync-storage model, ~75%) — explicitly handed to Codex to challenge.

### Prompt for Next Session

```
Read docs/plans/2026-07-21-feat-headless-service-core-plan.md and
docs/plans/2026-07-21-codex-plan-review-handoff.md. I ran the Codex plan review —
here are its findings:

[PASTE CODEX FINDINGS]

Fold the valid ones into the plan (note any you reject and why), then let's start
/workflows:work Session 1 (Foundations: deps + config.py + db.py + migrate.py +
migrations/001_init.sql + pytest DB fixtures).
```
