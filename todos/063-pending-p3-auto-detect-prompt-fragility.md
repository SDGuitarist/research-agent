---
status: done
priority: p3
issue_id: "063"
tags: [code-review, quality]
dependencies: []
---

# P3: Auto-detect prompt fragility — verbose LLM responses fall through

## Problem Statement

`auto_detect_context()` in `context.py:169-183` expects the LLM to reply with just a context name or "none". But LLMs sometimes add explanations. A response like "I think pfe is the best match because..." falls through to "unrecognized answer" and returns None. This is safe (falls back to no context) but may be annoying if it happens frequently.

## Findings

- Flagged by: kieran-python-reviewer (MEDIUM)
- Acknowledged in HANDOFF.md as a known risk
- Current behavior is safe — worst case is running without context when one should have been selected
- The `cleaned = answer.strip("\"'")` handles quoted responses already

## Proposed Solutions

### Option A: Add substring word matching as fallback
After the exact/quoted checks fail, check if any valid context name appears as a word in the response.
```python
for valid_lower, original_name in valid_names.items():
    if valid_lower in answer.split():
        logger.info("Auto-detect: extracted context '%s' from verbose response", original_name)
        return CONTEXTS_DIR / f"{original_name}.md"
```
- Pros: Catches the "I think pfe is..." pattern
- Cons: Could false-positive if context name is a common word
- Effort: Small (4 lines)
- Risk: Low (only triggers after exact match fails)

### Option B: Leave as-is (accepted risk)
- Pros: Zero risk, safe fallback
- Cons: Might miss correct context on verbose responses
- Effort: None

## Recommended Action

Option A if auto-detect proves unreliable in practice. Otherwise Option B is fine.

## Technical Details

- **Affected files:** `research_agent/context.py`

## Acceptance Criteria

- [ ] Decision: monitor or implement substring matching
- [ ] If implemented: test with "I think pfe is best" response

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-26 | Created from code review | Known risk from work phase |
