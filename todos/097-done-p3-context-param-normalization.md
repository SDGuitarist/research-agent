---
status: done
priority: p3
issue_id: "097"
tags: [code-review, robustness]
dependencies: []
unblocks: []
sub_priority: 2
---

# Context Parameter Defensive Normalization

## Problem Statement

The `context` parameter on `run_research` has three-way behavior (None/auto-detect, "none"/skip, "<name>"/specific). If an LLM sends `"None"`, `"null"`, or `"NONE"` (common LLM outputs), these would be treated as context name lookups and fail with a confusing error.

## Findings

- **Source:** agent-native-reviewer
- **File:** `research_agent/mcp_server.py`, lines 29-44

## Proposed Solutions

### Option A: Normalize before passing through (Recommended)
```python
if context is not None:
    context = context.strip().lower()
    if context in ("null", ""):
        context = None
```
- **Effort:** Small (3 lines)
- **Risk:** None

## Acceptance Criteria

- [ ] `"None"`, `"null"`, `"NONE"`, `""` all treated as auto-detect (None)
- [ ] `"none"` still skips context loading
- [ ] Valid context names still work

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-28 | Created from agent-native-reviewer | LLM-friendly input handling |
