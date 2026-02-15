---
status: rejected
triage_reason: "Rejected — foundation code for future cycles, not dead code"
priority: p2
issue_id: "004"
tags: [code-review, simplicity, dead-code]
dependencies: []
---

# ~270 lines of dead code to remove

## Problem Statement

Multiple functions and classes are defined but never called by the pipeline. This is YAGNI -- built for hypothetical future needs that don't exist yet.

## Findings

- **Simplicity reviewer**: Identified ~270 lines of dead code across 4 files.
- **Pattern reviewer**: `update_gap()` duplicates what `_update_gap_states` already does.
- **Architecture strategist**: `validate_gaps()` only caller is unused `update_gap()`.

**Dead code locations:**
1. `schema.py:228-362` -- `detect_cycles()`, `sort_gaps()`, `SortedGaps` (~135 lines)
2. `schema.py:157-225` -- `validate_gaps()` (~69 lines, only caller is dead `update_gap`)
3. `state.py:71-118` -- `update_gap()` (~48 lines, never called in pipeline)
4. `errors.py:37-39` -- `ContextAuthError` (~4 lines, never raised)

## Proposed Solutions

### Option A: Remove all dead code (Recommended)
Delete all four items and their corresponding tests.
- **Pros**: ~270 LOC removed, cleaner codebase
- **Cons**: If these features are needed later, they must be re-implemented
- **Effort**: Small
- **Risk**: Low (no callers exist)

### Option B: Keep but mark as planned
Add `# TODO: Wire into pipeline when dependency ordering is needed` comments.
- **Pros**: Preserves work already done
- **Cons**: Dead code accumulates, confuses readers
- **Effort**: Small
- **Risk**: None

## Recommended Action

_To be filled during triage._

## Technical Details

- **Affected files**: `research_agent/schema.py`, `research_agent/state.py`, `research_agent/errors.py`
- **Tests to remove**: Corresponding test classes in `test_schema.py`, `test_state.py`, `test_errors.py`

## Acceptance Criteria

- [ ] No dead functions remain in production code
- [ ] Corresponding dead tests removed
- [ ] All remaining tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-15 | Created from code review | 3/7 agents flagged dead code |

## Resources

- Simplicity review: "Total potential LOC reduction: ~530 lines"
