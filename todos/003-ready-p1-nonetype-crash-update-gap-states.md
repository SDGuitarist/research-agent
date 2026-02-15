---
status: ready
triage_reason: "Accepted — runtime crash if called before gap check"
priority: p1
issue_id: "003"
tags: [code-review, correctness]
dependencies: []
---

# NoneType crash in _update_gap_states

## Problem Statement

`agent.py:92` calls `{g.id for g in self._current_research_batch}` but `_current_research_batch` can be `None` if `_update_gap_states` is called before the gap check runs. The guard on line 89 only checks `schema_result`, not `_current_research_batch`.

## Findings

- **Python reviewer**: `TypeError: 'NoneType' is not iterable` if called before gap check.
- **Architecture strategist**: Temporal coupling between pre-research and post-research phases.

**File:** `research_agent/agent.py:92`

## Proposed Solutions

### Option A: Add None guard (Recommended)
```python
if not schema_result or self._current_research_batch is None:
    return
```
- **Pros**: Minimal change, prevents crash
- **Cons**: None
- **Effort**: Small
- **Risk**: Low

### Option B: Pass batch as parameter instead of instance state
```python
def _update_gap_states(self, decision: str, batch: tuple[Gap, ...]) -> None:
```
- **Pros**: Eliminates temporal coupling, makes data flow explicit
- **Cons**: Requires updating all callers
- **Effort**: Medium
- **Risk**: Low

## Recommended Action

_To be filled during triage._

## Technical Details

- **Affected files**: `research_agent/agent.py`
- **Components**: Gap state management

## Acceptance Criteria

- [ ] `_update_gap_states` does not crash when `_current_research_batch` is None
- [ ] All 571 tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-15 | Created from code review | 2/7 agents flagged this issue |

## Resources

- File: `research_agent/agent.py:88-92`
