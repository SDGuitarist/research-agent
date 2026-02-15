---
status: complete
priority: p2
issue_id: "028"
tags: [code-review, performance, async]
dependencies: []
---

# extract_all() Blocks Event Loop

## Problem Statement

`extract_all()` in `extract.py` uses CPU-intensive libraries (trafilatura, readability-lxml) but is called directly from async context without `asyncio.to_thread()`. This blocks the event loop for 3-10s depending on page count and size.

## Findings

- **Source:** Performance Oracle agent
- **Location:** `research_agent/extract.py` (extract_all), `research_agent/agent.py` (call site)

## Proposed Solutions

### Option A: Wrap in asyncio.to_thread (Recommended)
```python
results = await asyncio.to_thread(extract_all, pages)
```
- **Effort:** Small (15 min)

## Acceptance Criteria

- [ ] `extract_all` runs in a thread pool, not on the event loop
- [ ] All tests pass
