---
status: done
priority: p2
issue_id: "045"
tags: [code-review, performance]
dependencies: []
---

# P2: Retry queries searched sequentially — should be parallel

## Problem Statement

`_try_coverage_retry()` at `agent.py:461-473` searches up to 3 retry queries sequentially in a `for` loop. Each Tavily API call takes 1-3 seconds, so 3 sequential queries add 3-9 seconds wall-clock time. The existing `_search_sub_queries()` method already solves this with parallel, semaphore-bounded search.

## Findings

- Flagged by: performance-oracle, architecture-strategist, pattern-recognition-specialist
- `_search_sub_queries()` at agent.py:291-328 does exactly this pattern with `asyncio.gather` + semaphore
- The retry could reuse `_search_sub_queries()` directly or follow the same pattern

## Proposed Solutions

### Option A: Reuse `_search_sub_queries()` (Recommended)
Pass retry queries to the existing method, which already handles parallel search, dedup, and error logging.
- Pros: Eliminates duplication, proven code
- Cons: Minor interface mismatch (`per_sq_sources` vs `RETRY_SOURCES_PER_QUERY`)
- Effort: Small
- Risk: Low

### Option B: Add `asyncio.gather` in `_try_coverage_retry`
Write a parallel search loop inline.
- Pros: Self-contained
- Cons: Duplicates `_search_sub_queries` pattern
- Effort: Small
- Risk: Low

## Technical Details

- **File:** `research_agent/agent.py:461-473`
- Saves: 2-6 seconds wall-clock time per retry

## Acceptance Criteria

- [ ] Retry queries searched in parallel (not sequential for loop)
- [ ] Deduplication still works correctly
- [ ] Per-query search failures still non-fatal
- [ ] All tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-25 | Created from review | — |
