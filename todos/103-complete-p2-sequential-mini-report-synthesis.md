---
status: complete
priority: p2
issue_id: "103"
tags: [code-review, performance]
dependencies: []
unblocks: []
sub_priority: 2
---

# Sequential mini-report synthesis wastes 10-25s wall-clock time

## Problem Statement

In `_run_iteration()`, mini-report synthesis calls run sequentially in a for-loop. Each `synthesize_mini_report()` makes a blocking API call taking 3-8s. With 3 queries in standard mode, this is 9-24s sequential when the calls are fully independent.

## Findings

- **performance-oracle**: Critical perf issue — single largest latency win available

**Location:** `research_agent/agent.py:311-329`

## Proposed Solutions

### Option A: Parallelize with asyncio.gather + semaphore (Recommended)
Replace the sequential for-loop with `asyncio.gather()` + semaphore, matching the pattern in `_search_sub_queries()`.

```python
sem = asyncio.Semaphore(MAX_CONCURRENT_SUB_QUERIES)

async def _synthesize_one(q, title):
    async with sem:
        try:
            return await asyncio.to_thread(synthesize_mini_report, ...)
        except _SynthesisError as e:
            logger.warning("Mini-report failed for '%s': %s", q, e)
            return None

results = await asyncio.gather(*[_synthesize_one(q, t) for q, t in query_titles])
appended_sections = [r for r in results if r is not None]
```

- **Pros:** 60-70% latency reduction (15s → 5s), reuses existing pattern
- **Cons:** Slightly more complex control flow
- **Effort:** Small
- **Risk:** Low — rate limits may throttle, but semaphore caps concurrency

## Acceptance Criteria

- [ ] Mini-report synthesis runs in parallel with bounded concurrency
- [ ] Error handling preserved (per-query failure skips that section)
- [ ] Standard mode wall-clock time for iteration reduced
