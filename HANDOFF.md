# HANDOFF — Research Agent

**Date:** 2026-03-03
**Branch:** `main`
**Phase:** Cycle 21 complete — compound phase done

## Current State

Cycle 21 (Tiered Model Routing) is fully complete through the compound phase. Added `planning_model` field to `ResearchMode` routing 7 planning call sites to Haiku while 8 synthesis sites stay on Sonnet. Review found 5 issues (0 P1, 3 P2, 2 P3), all fixed. Solution documented, learnings propagated. 874 tests passing.

## Key Artifacts

| Phase | Location |
|-------|----------|
| Brainstorm | `docs/brainstorms/2026-03-02-tiered-model-routing-brainstorm.md` |
| Plan | `docs/plans/2026-03-02-feat-tiered-model-routing-plan.md` |
| Review | `docs/reviews/cycle-21/REVIEW-SUMMARY.md` |
| Solution | `docs/solutions/architecture/tiered-model-routing-planning-vs-synthesis.md` |

## Deferred Items

- Tier 2: Haiku for relevance scoring (needs A/B comparison data)
- Tier 3: Haiku for summarization (deferred indefinitely — too risky)
- `validate_query_list()` on `refine_query()` output (pre-existing gap, low priority)
- Standalone `generate_followups` MCP tool (agent-native parity)
- `iteration_sections: tuple[str, ...]` structured field on ResearchResult
- Per-query source count observability
- Double-sanitization idempotency risk (standing risk from Cycle 20)
- Update `cost_estimate` strings after real usage data collected
- Monitor Haiku decompose quality on first 10-20 real runs (feed-forward from review)

## Three Questions (Compound Phase)

1. **Hardest pattern to extract?** The relationship between "static task-based routing" as a general pattern and the specific decision about where to draw the planning/synthesis boundary. The transferable insight is "classify pipeline stages by quality sensitivity, not by module."

2. **What was rejected?** Detailed per-call-site latency benchmarks — pre-production estimates would imply false precision.

3. **Least confident about?** The interaction between `planning_model` and the iteration system (Cycle 20). If iteration quality degrades on complex topics, the root cause might be Haiku's planning quality rather than iteration logic — the debugging path isn't obvious because model routing is invisible at the `iterate.py` level.

## Prompt for Next Session

```
Read HANDOFF.md for context. This is Research Agent, a Python CLI that searches the web and generates structured reports with citations using Claude. Cycle 21 (tiered model routing) is complete. Pick the next feature or improvement from the deferred items list, or propose something new.
```
