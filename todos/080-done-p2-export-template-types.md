---
status: done
priority: p2
issue_id: "080"
tags: [code-review, agent-native, api]
dependencies: []
unblocks: []
sub_priority: 4
---

# P2: Export ReportTemplate and ContextResult from package `__init__.py`

## Problem Statement

`ReportTemplate`, `ContextResult`, and `ContextStatus` are not exported from `research_agent/__init__.py`. A programmatic agent importing the package gets `ImportError` when trying `from research_agent import ReportTemplate`. The only way to reach these types is via internal module paths (`from research_agent.context_result import ReportTemplate`), which violates discoverability.

## Findings

- Flagged by: agent-native-reviewer (Finding 1 + Finding 5)
- These types are used by the public-facing `ResearchAgent` class and `load_full_context()` function
- The `ResearchResult` dataclass IS exported, but the input types are not

## Proposed Solutions

### Option A: Add to `__init__.py` imports and `__all__` (Recommended)

```python
from .context_result import ContextResult, ContextStatus, ReportTemplate
```

Add all three to the `__all__` list.

- **Pros:** Standard Python package convention, enables programmatic use
- **Cons:** Slightly larger public API surface
- **Effort:** Small (2 line changes)
- **Risk:** Low

## Technical Details

**Affected files:**
- `research_agent/__init__.py` — add imports and `__all__` entries

## Acceptance Criteria

- [ ] `from research_agent import ReportTemplate, ContextResult, ContextStatus` works
- [ ] Existing tests still pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-27 | Created from code review | Flagged by Agent-Native Reviewer |
