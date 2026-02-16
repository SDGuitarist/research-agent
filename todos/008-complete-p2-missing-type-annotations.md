---
status: complete
triage_reason: "Accepted — untyped instance state and missing param annotation"
priority: p2
issue_id: "008"
tags: [code-review, quality, types]
dependencies: []
---

# Missing type annotations in agent.py

## Problem Statement

Three items in `agent.py` lack type annotations:
- Line 64: `self._current_schema_result = None` (should be `SchemaResult | None`)
- Line 65: `self._current_research_batch = None` (should be `tuple[Gap, ...] | None`)
- Line 67: `_already_covered_response(self, schema_result)` missing param type

## Findings

- **Python reviewer**: Untyped instance state, missing parameter annotation.

**File:** `research_agent/agent.py:64-67`

## Proposed Solutions

### Option A: Add type annotations (Recommended)
```python
self._current_schema_result: SchemaResult | None = None
self._current_research_batch: tuple[Gap, ...] | None = None
def _already_covered_response(self, schema_result: SchemaResult) -> str:
```
- **Effort**: Small | **Risk**: Low

## Acceptance Criteria

- [ ] All new instance attributes and methods have type annotations
- [ ] All tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-15 | Created from code review | |
