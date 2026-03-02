---
status: complete
priority: p2
issue_id: "104"
tags: [code-review, performance, reliability]
dependencies: []
unblocks: []
sub_priority: 3
---

# No overall timeout for iteration phase — 8-minute worst case

## Problem Statement

The iteration pipeline chains multiple timeout-sensitive operations (generation 30s, search, fetch/extract 60s, synthesis 120s x 3). With degraded API, the total could reach ~8 minutes with no feedback. There is no overall timeout cap on the iteration phase.

## Findings

- **performance-oracle**: Recommended safety net — prevents degraded-API worst case

**Location:** `research_agent/agent.py:862-876`

## Proposed Solutions

### Option A: Wrap iteration in asyncio.wait_for (Recommended)
```python
try:
    result, iteration_sources_added = await asyncio.wait_for(
        self._run_iteration(query, result, evaluation),
        timeout=180.0,  # 3-minute cap
    )
except asyncio.TimeoutError:
    logger.warning("Iteration timed out after 180s")
    self._iteration_status = "error"
```

- **Pros:** Prevents worst-case hang, user gets main report within bounded time
- **Cons:** Adds a timeout constant; hard failures vs. partial results
- **Effort:** Small
- **Risk:** Low — main report always available

## Acceptance Criteria

- [ ] Overall iteration timeout added (~180s)
- [ ] Timeout logged as warning
- [ ] Main report returned unchanged on timeout
- [ ] `iteration_status` set to "error" on timeout
