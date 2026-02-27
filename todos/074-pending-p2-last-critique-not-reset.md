---
status: done
priority: p2
issue_id: "074"
tags: [code-review, state-management]
dependencies: []
---

# P2: `_last_critique` not reset between runs

## Problem Statement

Six mutable run-state attributes are reset at top of `_research_async()`, but `_last_critique` is missing. Set at line 179, never cleared. A second run on the same agent that doesn't produce a critique reports the first run's critique.

## Findings

- Flagged by: pattern-recognition-specialist (P2)
- Related to completed todo 056 (state mutation fix) — this attribute was missed

## Fix

Add to the reset block at top of `_research_async()`:
```python
self._last_critique = None
```

## Acceptance Criteria

- [ ] `_last_critique` reset at start of each run
- [ ] Test: two runs on same agent, second run's `last_critique` reflects second run

## Technical Details

- **Affected files:** `research_agent/agent.py`
- **Effort:** Tiny (1 line)
