---
status: complete
triage_reason: "Accepted — mutable dict on frozen dataclass breaks immutability"
priority: p2
issue_id: "005"
tags: [code-review, architecture, frozen-dataclass]
dependencies: []
---

# Mutable dict on frozen Gap dataclass

## Problem Statement

`schema.py:39` defines `metadata: dict[str, str]` on a frozen dataclass. While the field itself can't be reassigned, the dict is mutable -- `gap.metadata["key"] = "value"` succeeds at runtime, breaking the immutability guarantee.

## Findings

- **Architecture strategist**: Other fields (`blocks`, `blocked_by`) correctly use immutable tuples.
- **Pattern reviewer**: Inconsistent with frozen dataclass convention.
- **Simplicity reviewer**: `metadata` field is never read by any pipeline code -- consider removing entirely.

**File:** `research_agent/schema.py:39`

## Proposed Solutions

### Option A: Remove metadata field entirely (Recommended)
The field is parsed but never used. YAGNI.
- **Pros**: Simplest fix, removes unused code
- **Cons**: Must re-add if metadata is needed later
- **Effort**: Small
- **Risk**: Low

### Option B: Use MappingProxyType for true immutability
```python
from types import MappingProxyType
metadata: MappingProxyType = field(default_factory=lambda: MappingProxyType({}))
```
- **Pros**: Preserves the field with true immutability
- **Cons**: More complex, field still unused
- **Effort**: Small
- **Risk**: Low

## Acceptance Criteria

- [ ] No mutable containers on frozen dataclasses
- [ ] All tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-15 | Created from code review | 3/7 agents flagged this |
