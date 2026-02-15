---
status: ready
triage_reason: "Accepted — violates core project convention, 5/7 agents flagged"
priority: p1
issue_id: "001"
tags: [code-review, quality, convention]
dependencies: []
---

# Bare `except Exception` in count_tokens

## Problem Statement

`token_budget.py:28` uses `except Exception:` which violates the project convention "Never bare `except Exception`". This silently swallows configuration errors, auth failures, and network issues, hiding real bugs behind a fallback estimate.

## Findings

- **Python reviewer**: Catches overly broad exceptions including `MemoryError`, `SystemExit` subclasses. Hides API key misconfiguration.
- **Security sentinel**: Silently catches auth errors, increasing exposure window.
- **Architecture strategist**: Only `except Exception` violation in new code (3 more exist in pre-existing `synthesize.py`).

**File:** `research_agent/token_budget.py:28`

## Proposed Solutions

### Option A: Narrow to specific exceptions (Recommended)
```python
except (ImportError, AttributeError, anthropic.APIError, anthropic.AuthenticationError, OSError) as exc:
    logger.debug("Token counting fallback: %s", exc)
    return max(1, len(text) // 4)
```
- **Pros**: Follows project convention, logs the reason for fallback
- **Cons**: May miss unexpected exception types from anthropic SDK
- **Effort**: Small
- **Risk**: Low

### Option B: Switch to char-based estimate only
Remove the API call entirely; use `len(text) // 4` as primary.
- **Pros**: Eliminates the exception handling entirely, faster
- **Cons**: Less accurate (but budget allocation is approximate anyway)
- **Effort**: Small
- **Risk**: Low

## Recommended Action

_To be filled during triage._

## Technical Details

- **Affected files**: `research_agent/token_budget.py`
- **Components**: Token budget allocation

## Acceptance Criteria

- [ ] No bare `except Exception` in `token_budget.py`
- [ ] Fallback reason logged at DEBUG level
- [ ] All 571 tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-15 | Created from code review | 5/7 agents flagged this issue |

## Resources

- Project convention: CLAUDE.md "Never bare `except Exception`"
