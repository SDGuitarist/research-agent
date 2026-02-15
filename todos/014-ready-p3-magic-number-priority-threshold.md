---
status: ready
triage_reason: "Accepted — magic number 6 will break silently if priorities change"
priority: p3
issue_id: "014"
tags: [code-review, quality]
dependencies: []
---

# Magic number 6 for priority threshold

## Problem Statement

`token_budget.py:113` hardcodes `6` as the "never prune" threshold. This matches `COMPONENT_PRIORITY["instructions"] == 6` but will break silently if priority levels change.

## Proposed Solutions

Define `NEVER_PRUNE_THRESHOLD = 6` constant.
- **Effort**: Small | **Risk**: Low

## Acceptance Criteria

- [ ] No magic numbers for priority thresholds
- [ ] All tests pass
