---
status: done
triage_reason: "Accepted — 8-16 unnecessary API calls per run, easy fix"
priority: p1
issue_id: "002"
tags: [code-review, performance]
dependencies: []
---

# New Anthropic client created per count_tokens() call

## Problem Statement

`token_budget.py:21` creates a new `anthropic.Anthropic()` client on every call to `count_tokens()`. During `allocate_budget`, this is called 3-5 times per synthesis. Each instantiation opens a new connection pool with TLS handshake. A standard/deep run hits 8-16 unnecessary API round-trips purely for token counting.

## Findings

- **Performance oracle**: P0 issue. Eliminates 8-16 unnecessary API calls per run, saves 2-8 seconds of latency.
- **Python reviewer**: Wasteful HTTP client creation per invocation.
- **Architecture strategist**: `ResearchAgent` already has `self.client` but never passes it to token counting layer.
- **Security sentinel**: API key accessed from environment repeatedly.

**File:** `research_agent/token_budget.py:20-27`

## Proposed Solutions

### Option A: Use char-based estimate as primary (Recommended)
Replace API-based counting with `len(text) // 4` since budget allocation is inherently approximate.
- **Pros**: Zero API calls, fastest, simplest
- **Cons**: Less precise (but the fallback already uses this)
- **Effort**: Small
- **Risk**: Low

### Option B: Cache client at module level
```python
_client: anthropic.Anthropic | None = None
def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    return _client
```
- **Pros**: Reuses connection pool, still uses precise API counting
- **Cons**: Module-level mutable state, still makes API calls
- **Effort**: Small
- **Risk**: Low

### Option C: Accept client parameter
- **Pros**: Follows dependency injection, testable
- **Cons**: Requires threading client through callers
- **Effort**: Medium
- **Risk**: Low

## Recommended Action

_To be filled during triage._

## Technical Details

- **Affected files**: `research_agent/token_budget.py`
- **Components**: Token counting, budget allocation

## Acceptance Criteria

- [ ] No new `Anthropic()` client created per `count_tokens()` call
- [ ] Token counting latency reduced (no API round-trips for budget estimation)
- [ ] All 571 tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-15 | Created from code review | 4/7 agents flagged this issue |

## Resources

- Performance analysis: 8-16 API calls per run eliminated
