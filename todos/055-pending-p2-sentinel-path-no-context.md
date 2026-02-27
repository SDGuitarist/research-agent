---
status: done
priority: p2
issue_id: "055"
tags: [code-review, architecture]
dependencies: []
---

# P2: Replace magic sentinel Path("__no_context__") with explicit parameter

## Problem Statement

`_effective_context_path` in `agent.py:100-109` returns `Path("__no_context__")` as a sentinel to prevent `decompose_query()` from falling back to the default context file. This relies on no file named `__no_context__` existing on disk — fragile and non-obvious.

The root cause is that `decompose_query()` loads context internally via `load_full_context()`, so the agent cannot control context loading for decomposition without a workaround.

## Findings

- Flagged by: kieran-python-reviewer (CRITICAL), architecture-strategist (HIGH), code-simplicity-reviewer (MEDIUM)
- The sentinel works because `load_full_context` checks `.exists()` and returns `not_configured`
- Correctness depends on implementation details of the callee
- No documentation or type annotation indicating the path might be a sentinel

## Proposed Solutions

### Option A: Pass ContextResult to decompose_query (Recommended)
Change `decompose_query()` to accept a `ContextResult` or `str | None` content instead of a `Path`. The agent already loads context — pass the result directly.
```python
# decompose.py — change signature:
def decompose_query(client, query, context_content: str | None = None, ...):
    # use context_content directly instead of loading from file
```
- Pros: Eliminates sentinel entirely, removes decompose.py's dependency on load_full_context
- Cons: Changes decompose_query API, requires test updates
- Effort: Medium (~20 lines across agent.py, decompose.py, tests)
- Risk: Low

### Option B: Add no_context parameter to decompose_query
```python
def decompose_query(client, query, context_path=None, no_context=False, ...):
    if no_context:
        ctx_content = None
    else:
        ctx_content = load_full_context(context_path).content
```
- Pros: Minimal API change, explicit
- Cons: Still has decompose loading its own context
- Effort: Small (~10 lines)
- Risk: Low

### Option C: Named constant for sentinel
```python
_NO_CONTEXT_PATH = Path("__no_context__")
```
- Pros: Minimal change
- Cons: Doesn't fix the underlying design issue
- Effort: Tiny (2 lines)
- Risk: Low

## Recommended Action

Option A — cleanest design, eliminates the dependency direction violation.

## Technical Details

- **Affected files:** `research_agent/agent.py`, `research_agent/decompose.py`, `tests/test_decompose.py`

## Acceptance Criteria

- [ ] `_effective_context_path` property removed
- [ ] `Path("__no_context__")` no longer appears in codebase
- [ ] `decompose_query()` accepts context content directly
- [ ] All existing tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-26 | Created from code review | Three agents flagged this independently |
