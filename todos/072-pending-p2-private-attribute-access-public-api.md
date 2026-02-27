---
status: done
priority: p2
issue_id: "072"
tags: [code-review, api, encapsulation]
dependencies: []
---

# P2: Public API accesses private attributes `_last_source_count` and `_last_gate_decision`

## Problem Statement

`run_research_async()` in `__init__.py:113-114` reads `agent._last_source_count` and `agent._last_gate_decision` — underscore-prefixed private attributes. Couples public API to internal implementation details.

## Findings

- Flagged by: kieran-python-reviewer (P2), pattern-recognition-specialist (P2)

## Fix

Add public read-only properties to `ResearchAgent`:
```python
@property
def last_source_count(self) -> int:
    return self._last_source_count

@property
def last_gate_decision(self) -> str | None:
    return self._last_gate_decision
```

Then update `__init__.py` to use `agent.last_source_count` and `agent.last_gate_decision`.

## Acceptance Criteria

- [ ] Public API uses property access, not `_private` access
- [ ] Properties added to `ResearchAgent`

## Technical Details

- **Affected files:** `research_agent/agent.py`, `research_agent/__init__.py`
- **Effort:** Small (~10 lines)
