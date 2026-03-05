# HANDOFF — Research Agent

**Date:** 2026-03-05
**Branch:** `main`
**Phase:** Tier 2 A/B test complete — promoting Haiku relevance scoring to permanent

## Current State

Tier 2 A/B test (Haiku for relevance scoring) complete. Ran 9 queries with `RELEVANCE_MODEL=claude-haiku-4-5-20251001` env var override. Zero decision flips, comparable source filtering. Now promoting to a permanent `relevance_model` field on `ResearchMode` and removing the env var hack. 891 tests passing.

### Session Commits
1. `feat(relevance): add RELEVANCE_MODEL env var for A/B testing` — temporary override + test script

### Tier 2 A/B Results: Haiku vs Sonnet Relevance Scoring (9 queries, standard mode)

| Report | Sonnet sources | Haiku sources | Decision change? |
|--------|---------------|---------------|-----------------|
| lodge | 6 | 7 | No (full→full) |
| restaurants | 7 | 10 | No (full→full) |
| zoning | 12 | 7 | No (full→full) |
| pendry | 9 | 7 | No (full→full) |
| hoteldel | 2 | 3 | No (short→short) |
| luxury-trends | 7 | 7 | No (full→full) |
| grant-writing | 12 | 12 | No (full→full) |
| ai-jobs | 12 | 12 | No (full→full) |
| ai-filmmaking | 11 | 9 | No (full→full) |

**Verdict:** Zero decision flips. Source count differences are search variability, not scoring divergence. Haiku scores TripAdvisor/Yelp/YouTube consistently low (1/5) just like Sonnet. Safe to promote.

## Key Artifacts

| Phase | Location |
|-------|----------|
| A/B test script | `scripts/ab-test-relevance-haiku.sh` |
| A/B test log | `reports/ab-test-haiku-relevance.log` |
| Haiku-scored reports | `reports/*_2026-03-05_10[3-9]*.md` and `reports/*_2026-03-05_11*.md` |
| Sonnet-scored reports | `reports/*_2026-03-05_09*.md` and `reports/*_2026-03-05_10[0-2]*.md` |

## Deferred Items

- ~~Tier 2: Haiku for relevance scoring~~ **Done** — A/B tested, promoting to permanent
- Tier 3: Haiku for summarization (deferred indefinitely — too risky)
- `validate_query_list()` on `refine_query()` output (pre-existing gap, low priority)
- Standalone `generate_followups` MCP tool (agent-native parity)
- `iteration_sections: tuple[str, ...]` structured field on ResearchResult
- Per-query source count observability
- Double-sanitization idempotency risk (standing risk from Cycle 20)
- Update `cost_estimate` strings after real usage data collected

## Three Questions

1. **Hardest implementation decision?** Whether to use an env var or a dataclass field for the A/B test. Chose env var for temporary testing (no schema change), then promote to permanent field once validated. This two-step approach avoids shipping untested permanent changes.

2. **What did you consider changing but left alone?** Considered adding `relevance_model` directly to `ResearchMode` from the start (skipping the env var). But that would have changed the frozen dataclass, required test updates, and committed to the change before validating it. The env var let us test without commitment.

3. **Least confident about going into next phase?** The hoteldel query stayed `short_report` with both models (2 vs 3 sources). This isn't a model issue — it's a hard query (future events for a specific hotel). But the zoning query dropped from 12→7 sources with Haiku scoring, which is worth monitoring to see if Haiku is slightly more aggressive on borderline sources.

## Prompt for Next Session

```
Read HANDOFF.md for context. Tier 2 A/B test passed — Haiku relevance scoring validated. Add `relevance_model` field to ResearchMode (default to AUTO_DETECT_MODEL), use it in evaluate_sources, remove RELEVANCE_MODEL env var hack. Relevant files: research_agent/modes.py, research_agent/relevance.py, tests/test_relevance.py, tests/test_modes.py.
```
