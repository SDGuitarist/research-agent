---
status: complete
triage_reason: "Accepted — ~15 lines of identical pruning logic in two places"
priority: p2
issue_id: "006"
tags: [code-review, quality, duplication]
dependencies: []
---

# Token budget pruning logic duplicated in synthesize.py

## Problem Statement

The budget pruning logic (build components dict, call `allocate_budget`, iterate `budget.pruned`, truncate sources/business_context) appears nearly identically in both `synthesize_report` (lines 72-92) and `synthesize_final` (lines 375-396).

## Findings

- **Pattern reviewer**: ~15 lines of identical pruning loop in two functions.
- **Simplicity reviewer**: Could be extracted to `_apply_budget_pruning()`.

**Files:** `research_agent/synthesize.py:72-92` and `375-396`

## Proposed Solutions

### Option A: Extract helper function (Recommended)
Create `_apply_budget(components, max_tokens, reserved) -> dict[str, str]` that returns truncated content.
- **Pros**: Single source of truth, DRY
- **Cons**: One more function to navigate
- **Effort**: Small
- **Risk**: Low

## Acceptance Criteria

- [ ] Budget pruning logic exists in one place
- [ ] Both `synthesize_report` and `synthesize_final` use the shared helper
- [ ] All tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-15 | Created from code review | 2/7 agents flagged duplication |
