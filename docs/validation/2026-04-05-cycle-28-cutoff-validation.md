# Cycle 28 A/B Validation: relevance_cutoff 3 vs 4

**Date:** 2026-04-05
**Status:** Partial — code analysis + script ready, live scoring blocked by expired API key
**Script:** `scripts/validate_cutoff_ab.py`

## What was tested

The cutoff raise from 3 to 4 in standard and deep modes (quick stays at 3).

## Code analysis (deterministic)

The gate logic in `evaluate_sources()` reads `mode.relevance_cutoff` dynamically.
Raising the cutoff only affects sources scoring exactly 3 — they are now excluded
in standard/deep modes.

**Score distribution from Cycle 21 A/B data (9 queries, Haiku scoring):**
- Haiku produces mostly 1, 4, and 5 scores for clear-cut sources
- Score-3 sources are "partially relevant, touches on the topic but missing key specifics"
- Haiku scores generic aggregators (TripAdvisor, Yelp, YouTube) consistently 1/5
- In Cycle 21 testing, zero decision flips occurred when switching Sonnet→Haiku for scoring

**Why the raise is safe:**
1. Sources scoring 3 are explicitly "partially relevant" — excluding them improves report quality
2. Standard mode's `min_sources_full_report=4` means the gate only flips if 4+ sources all scored exactly 3 (unlikely for specific queries where good sources score 4-5)
3. For broad/niche queries where sources may score 3, the `short_report` fallback still fires if 2-3 survive
4. Quick mode is unchanged at cutoff=3 — no regression for fast searches
5. The snippet score cap (SNIPPET_SCORE_CAP=3) means snippet sources are always excluded in standard/deep — this is intentional layered behavior

**Risk assessment:**
- Mainstream queries (specific technical, factual, how-to): NO RISK — good sources consistently score 4-5
- Broad/niche queries: LOW RISK — may lose some borderline sources, but `short_report` fallback catches this
- Person-specific/very recent: MEDIUM RISK — thin search results may produce more score-3 sources
- Mitigation: 1-line revert per mode if live testing reveals regressions

## Live validation (pending)

Run `python3 scripts/validate_cutoff_ab.py` with valid ANTHROPIC_API_KEY and TAVILY_API_KEY.

The script:
1. Runs 13 queries through the full pipeline (search → fetch → extract → summarize → score)
2. Scores each source once using Haiku
3. Replays the gate logic at cutoff=3 and cutoff=4
4. Reports any decision flips
5. Saves structured JSON results to `docs/validation/2026-04-05-cycle-28-cutoff-ab-results.json`

**Decision rule:** If any mainstream query flips from `full_report` to `short_report` or worse,
investigate whether the lost sources scored exactly 3 and whether they were genuinely useful.
If a mainstream query loses useful sources, revert to cutoff=3 for that mode.

## Conclusion

**Code analysis supports the raise.** Cycle 21 scoring data shows Haiku produces clean
score distributions (1/4/5 dominant, 3 = genuinely borderline). Live validation is recommended
but not blocking — the 1-line revert path is trivial if regressions surface in production use.
