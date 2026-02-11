---
title: "Source-Level Relevance Aggregation: Chunk Scoring vs Source Decisions"
date: 2026-02-10
category: logic-errors
tags:
  - relevance-gate
  - chunk-aggregation
  - source-survival
  - diagnostic-script
  - architectural-mismatch
module: research_agent/relevance.py, tests/test_relevance.py
symptoms: |
  Relevance gate survival rates at 11-41% (chunk-level). Reports under target word count.
  Boilerplate chunks (nav, footer, sidebar) scored low individually, dragging down sources
  that had relevant content in other chunks.
severity: high
summary: |
  The relevance gate scored individual chunk-summaries independently. A single web page
  chunked into 5 pieces created 5 separate scores. Fixed by adding _aggregate_by_source()
  that takes max score per URL. When a source passes, all its chunks survive.
  Result: 2x chunks reaching synthesizer (31->62), source survival stable (50%->53%).
---

# Source-Level Relevance Aggregation (Cycle 15)

## What Was Built

Changed relevance gate from **per-chunk** to **per-source** filtering. When a source passes, all its chunks survive.

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Chunks reaching synthesizer | 31 | 62 | **+100%** |
| Source survival rate | 50% | 53% | stable |
| Total tests | 341 | 350 | +9 |

## Problem: Unit Mismatch

### Diagnosis Method

Wrote `diagnose_relevance.py` — runs the full pipeline but intercepts the relevance gate to capture per-chunk scores. Ran 3 real deep-mode queries:

| Query | Chunks | Unique URLs | Chunk Survival | Source Survival (max) |
|---|---|---|---|---|
| SD corporate DJ | 76 | 30 | 41% | 50% |
| Wedding bands SD | 99 | 29 | 11% | 21% |
| Live music trends | 96 | 29 | 15% | 31% |

**Key finding:** Score 2 dominated (60-71 chunks per query). Most were boilerplate chunks from sources that had relevant content in other chunks.

Real example — `partyslate.com` (a relevant DJ directory):
```
Chunk 1 (listings):      score=4 KEEP
Chunk 2 (navigation):    score=2 DROP
Chunk 3 (sidebar):       score=2 DROP
Chunk 4 (footer):        score=2 DROP
Chunk 5 (related links): score=1 DROP
```

Old code dropped chunks 2-5 individually. Only chunk 1 survived.

### Root Cause

`evaluate_sources()` filtered per-chunk, but `synthesize.py` already groups by URL in `_build_sources_context()`. The unit of evaluation didn't match the unit of decision.

## Solution

Added `_aggregate_by_source()` helper in `relevance.py`:

```python
def _aggregate_by_source(summaries, scored_results):
    """Group chunk scores by URL, take max score per source."""
    by_url = {}
    for summary, result in zip(summaries, scored_results):
        # Handle exceptions from gather (default to score 3)
        score = 3 if isinstance(result, Exception) else result["score"]
        if summary.url not in by_url:
            by_url[summary.url] = {"score": score, "all_summaries": [], ...}
        entry = by_url[summary.url]
        entry["all_summaries"].append(summary)
        if score > entry["score"]:
            entry["score"] = score  # Keep max
    return list(by_url.values())
```

Modified `evaluate_sources()` to use source-level filtering:
```python
source_scores = _aggregate_by_source(summaries, scored_results)
for source in source_scores:
    if source["score"] >= mode.relevance_cutoff:
        surviving_sources.extend(source["all_summaries"])  # ALL chunks kept
total_scored = len(source_scores)  # Count unique URLs, not chunks
```

## Key Lesson: Score the Unit You Decide On

When data has hierarchy (chunks inside sources), the level you **score** must match the level you **decide** on.

- Before: Score chunks, decide on chunks, but downstream groups by source -> mismatch
- After: Score chunks, aggregate to sources (max), decide on sources -> aligned

General principle: if you must score at a finer grain than you decide, make aggregation explicit.

## Prevention Checklist

- When scoring hierarchical data, identify: which level drives the decision?
- Before fixing, diagnose with real data (not fixtures) — `diagnose_relevance.py` pattern
- Capture both levels of metrics (chunk count AND source count)
- Verify all data from passing groups survives downstream

## Files Changed

| File | Change |
|------|--------|
| `research_agent/relevance.py` | Added `_aggregate_by_source()`, modified `evaluate_sources()` |
| `tests/test_relevance.py` | +9 tests: `TestAggregateBySource` (4) + `TestSourceAggregation` (5) |

## Related

- Cycle 6: Relevance gate initial implementation (LESSONS_LEARNED.md)
- Cycle 10: Structured summaries (FACTS/QUOTES/TONE) that feed into scoring
- `diagnose_relevance.py`: Reusable diagnostic script (not committed to prod)
