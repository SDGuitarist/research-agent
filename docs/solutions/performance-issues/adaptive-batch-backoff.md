---
title: "Adaptive Batch Backoff Replaces Fixed API Delays"
date: 2026-02-15
category: performance-issues
tags: [rate-limiting, backoff, api-calls, batch-processing, latency]
module: relevance.py, summarize.py
symptoms: "Deep research runs took 6-9 seconds longer than necessary due to unconditional inter-batch sleep delays."
severity: low
summary: "Fixed inter-batch delays waste time when no rate limiting occurs. Adaptive backoff only sleeps after a 429, saving 6-9 seconds per deep run."
---

# Adaptive Batch Backoff Replaces Fixed API Delays

**Commit:** `0c44f95 Cycle 17: Session 4 — adaptive batch backoff`

## Problem

`relevance.py` and `summarize.py` both process sources in batches, making
multiple Claude API calls per run. Each module had a hard-coded `asyncio.sleep`
between every batch:

- `relevance.py` — 3.0s delay between scoring batches
- `summarize.py` — 1.5s delay between summarization batches

These delays fired unconditionally, even when no rate limiting was occurring.
A deep research run (12 sources, ~3 batches) accumulated 6-9 seconds of pure
dead time where the agent sat idle for no reason.

## Root Cause

The fixed delays were added defensively during early development to avoid
hitting Anthropic's 429 rate limits. The assumption was "sleeping is cheap,
rate limit errors are expensive." In practice, the rate limits were rarely
hit during normal operation, so the sleep calls just wasted time on every
single run.

## Solution

Replace unconditional delays with adaptive backoff using a boolean flag.
Only sleep before the next batch if the previous batch actually triggered
a 429 error.

### Pattern (pseudocode)

```python
hit_rate_limit = False

for batch in batches:
    if hit_rate_limit:
        await asyncio.sleep(BACKOFF_DELAY)
        hit_rate_limit = False

    try:
        results = await process_batch(batch)
    except RateLimitError:
        hit_rate_limit = True
        await asyncio.sleep(BACKOFF_DELAY)
        results = await process_batch(batch)  # retry once
```

### Why this works

- **No 429 encountered:** Batches fire back-to-back with zero delay.
- **429 encountered:** The current batch retries after a sleep, and the
  flag ensures the next batch also waits. Once a clean batch completes,
  the flag resets and delays stop again.
- **Worst case:** Identical to the old fixed-delay behavior (sleep every batch).
- **Best case:** Zero added latency (no rate limits hit).

## Results

| Scenario | Before | After | Saved |
|----------|--------|-------|-------|
| Deep run (12 sources, 3 batches) | ~9s dead time | ~0s | ~9s |
| Standard run (10 sources, 2 batches) | ~4.5s dead time | ~0s | ~4.5s |
| Quick run (4 sources, 1 batch) | ~0s (single batch) | ~0s | 0s |

Deep runs see the largest improvement because they have the most batches.

## Prevention

**General rule: do not add fixed delays to defend against rate limits.**

React to actual 429 responses instead. Fixed sleeps are a form of premature
optimization that trades guaranteed latency for hypothetical safety. The
adaptive boolean flag pattern shown above is simple, adds minimal code, and
only pays the cost when it needs to.

If you find yourself writing `await asyncio.sleep(N)` between API batches,
ask: "Am I actually hitting rate limits here?" If not, use the adaptive
pattern instead.
