---
status: done
triage_reason: "Accepted — no circular dependency risk, move to top-level per PEP 8"
priority: p3
issue_id: "021"
tags: [code-review, quality]
dependencies: []
---

# Inline imports in agent.py methods

## Problem Statement

`agent.py:84-86` and `186-187` use deferred imports inside method bodies for `schema`, `state`, and `staleness`. These modules don't import from `agent.py`, so there's no circular dependency risk. They should be top-level imports per PEP 8.

Note: The architecture reviewer argues these are intentional for keeping gap subsystem optional when `schema_path` is None. Consider this tradeoff.

## Proposed Solutions

### Option A: Move to top-level imports (Recommended)
- **Effort**: Small | **Risk**: Low

### Option B: Keep deferred (if optionality is valued)
Add a comment explaining why they are deferred.
- **Effort**: Small | **Risk**: None

## Acceptance Criteria

- [ ] Either imports moved to top-level, or comments explain the deferral
- [ ] All tests pass
