---
status: pending
priority: p2
issue_id: "091"
tags: [code-review, quality]
dependencies: []
unblocks: []
sub_priority: 2
---

# f-string Logger Calls in agent.py

## Problem Statement

Five `logger.warning()` calls in `agent.py` still use f-strings instead of `%s` formatting. This is inconsistent with the rest of the print-to-logging migration (which correctly uses `%s` placeholders) and defeats lazy evaluation — the string interpolation happens even when WARNING is not the active log level.

## Findings

- **Source:** kieran-python-reviewer
- **File:** `research_agent/agent.py`, lines 369, 698, 773, 851, 857
- **Evidence:**
  ```python
  logger.warning(f"Sub-query search failed: {e}, continuing")
  logger.warning(f"Skeptic review failed: {e}, continuing without it")
  logger.warning(f"Pass 2 search failed: {e}, continuing with existing results")
  logger.warning(f"Pass 2 processing failed: {e}, continuing with pass 1 results")
  logger.warning(f"Pass 2 search failed: {e}, continuing with pass 1 results")
  ```

## Proposed Solutions

### Option A: Convert to %s formatting (Recommended)
```python
logger.warning("Sub-query search failed: %s, continuing", e)
logger.warning("Skeptic review failed: %s, continuing without it", e)
logger.warning("Pass 2 search failed: %s, continuing with existing results", e)
logger.warning("Pass 2 processing failed: %s, continuing with pass 1 results", e)
logger.warning("Pass 2 search failed: %s, continuing with pass 1 results", e)
```
- **Effort:** Small (5 lines)
- **Risk:** None

## Acceptance Criteria

- [ ] All 5 logger.warning calls use `%s` placeholders
- [ ] No f-string logger calls remain in agent.py
- [ ] Tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-28 | Created from kieran-python-reviewer | Leftover from migration — pre-existing calls not updated |
