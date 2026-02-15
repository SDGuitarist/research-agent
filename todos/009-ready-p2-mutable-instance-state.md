---
status: done
triage_reason: "Accepted — temporal coupling creates fragile state management"
priority: p2
issue_id: "009"
tags: [code-review, architecture]
dependencies: []
---

# Mutable instance state coupling in ResearchAgent

## Problem Statement

`_current_schema_result` and `_current_research_batch` are set in `_research_async` (lines 206-207) and later read in `_update_gap_states` and `_evaluate_and_synthesize`. This creates temporal coupling -- if methods are called in wrong order, it silently uses stale/None state. If `research_async` is called twice on the same instance, state leaks across calls.

## Findings

- **Architecture strategist**: "Replace with local variable or dataclass passed through the pipeline."
- **Pattern reviewer**: "Set state in method A, read it in method B" is fragile.

**File:** `research_agent/agent.py:64-65, 206-207`

## Proposed Solutions

### Option A: Pass as parameters (Recommended)
```python
research_batch = self._pre_research_check()
# ... pipeline ...
self._update_gap_states(decision, research_batch, schema_result)
```
- **Effort**: Medium | **Risk**: Low

### Option B: Reset at start of each research call
Add `self._current_schema_result = None` at the top of `_research_async`.
- **Effort**: Small | **Risk**: Low

## Acceptance Criteria

- [ ] No temporal coupling between pre/post research phases
- [ ] All tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-15 | Created from code review | 2/7 agents flagged coupling |
