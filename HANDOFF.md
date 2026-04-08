# HANDOFF — Research Agent

**Date:** 2026-04-07
**Branch:** `main`
**Phase:** Cycle 29H COMPLETE. Ready for Cycle 29 or Codex code review.

## Current State

Cycle 29H (Codebase Hygiene — Audit-Driven Fixes) complete — 5 commits on main, 1034 tests passing. All 14 P2 findings from the 6-agent audit resolved across 5 sessions.

## Commits

| Commit | Session | Summary |
|--------|---------|---------|
| `86fc2ed` | 1 | GateDecision StrEnum, compute_gate_decision, ANTHROPIC_ERRORS, dropped_sources typing |
| `b8b5228` | 2 | _synthesis_errors context manager (4 functions), stale comment fix |
| `83d52aa` | 3 | Null bytes, sanitize_patterns, public APIs, httpx pre-check, thread-safe cache |
| `ff03878` | 4 | 10 new report_store tests, CLI help text fix |
| `26fd60a` | 5 | Concurrency tuning, nullcontext, inline instructions, EXTRACT_DOMAINS migration |

## Key Artifacts

| Phase | Location |
|-------|----------|
| Plan (revised 2x) | `docs/plans/2026-04-07-cycle-29h-codebase-hygiene-plan.md` |

## Public API Changes

- **`GateDecision` exported from `research_agent`** — intentional. Consumers need it to compare `result.status` against typed enum values (e.g., `GateDecision.FULL_REPORT`) instead of bare strings. `GateDecision` is a `StrEnum`, so `result.status == "full_report"` still works for backward compatibility, but the enum is the preferred comparison.

## Deferred Items

- **ANTHROPIC_ERRORS not yet consumed at all call sites** — Session 1c defined the tuple but Sessions 2-3 only consumed it in the synthesis context manager. The 10+ remaining `except (APIError, RateLimitError, ...)` blocks still use inline tuples. This is a mechanical replacement deferred to avoid bloating the hygiene cycle.
- **MCP `--cost` + `--critique-history` tools** (#123) — Cycle 31
- **A/B live validation** — run `scripts/validate_cutoff_ab.py` when API keys renewed
- **Session 5a acceptance check** — smoke test `--standard` query to verify no 429 cascade from higher concurrency. Revert is 1-line per file if needed.

## Three Questions

1. **Hardest implementation decision?** The EXTRACT_DOMAINS migration (Session 5d) — threading the parameter through agent.py → cascade.py while maintaining the zero-API-calls invariant when no context is loaded. The test updates were the trickiest part since existing tests assumed the hardcoded domains.
2. **What did you consider changing but left alone?** ANTHROPIC_ERRORS consumption at all 10+ call sites — it's a mechanical find-and-replace but touching that many files in a hygiene cycle increases review surface. Left for a future micro-cycle.
3. **Least confident about going into review?** The thread-safe Tavily client cache required autouse fixtures in test_cascade.py and test_search.py to reset the cache between tests. If any new Tavily-related tests are added without the fixture, they could see stale cached clients.

## Next Phase

Codex code review of branch `main` (5 commits from `86fc2ed` to `26fd60a`), then Cycle 29 (skeptic enforcement + score-aware refinement + evidence-tier labeling per entropy roadmap).

### Prompt for Next Session

```
Read HANDOFF.md for context. This is research-agent, a Python CLI research tool.
Cycle 29H complete (1034 tests). Next: Codex code review of the 5 hygiene commits,
then Cycle 29 — skeptic enforcement + score-aware refinement + evidence-tier labeling.
Start with /compound-start to load lessons and kick off.
```
