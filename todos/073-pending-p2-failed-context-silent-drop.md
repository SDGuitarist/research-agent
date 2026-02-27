---
status: done
priority: p2
issue_id: "073"
tags: [code-review, error-handling]
dependencies: []
---

# P2: `load_full_context` FAILED status silently drops to no-context

## Problem Statement

When `OSError` occurs reading a context file, `load_full_context()` returns `ContextResult.failed()`. The `__bool__` returns `False` for FAILED, so it's treated identically to NOT_CONFIGURED. A context file with permissions errors is silently treated as "no context" with no user-visible warning.

## Findings

- Flagged by: architecture-strategist (P2)
- User explicitly asked for a context (via `--context pfe`) but gets none with no warning

## Fix

In `agent.py`, after `_load_context_for()`:
```python
result = self._load_context_for(...)
if result.status == ContextStatus.FAILED:
    logger.warning("Context file could not be read: %s", result.error)
```

## Acceptance Criteria

- [ ] FAILED context produces a user-visible warning
- [ ] Research continues without context (current behavior)
- [ ] Test covers permissions error scenario

## Technical Details

- **Affected files:** `research_agent/agent.py`
- **Effort:** Small (~5 lines)
