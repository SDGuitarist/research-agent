---
status: complete
priority: p3
issue_id: "109"
tags: [code-review, quality, style]
dependencies: []
unblocks: []
sub_priority: 1
---

# Hoist SynthesisError import to module level and clean up agent.py

## Problem Statement

`SynthesisError` is lazily imported inside `_run_iteration()` with an unnecessary alias `_SynthesisError`. It should be imported at the module level where other errors from `.errors` are already imported. Also, `self._iteration_status = "skipped"` at line 861 is redundant with the reset at line 370.

## Findings

- **kieran-python-reviewer**: P3 — style inconsistency
- **code-simplicity-reviewer**: Confirmed — can add to existing import line 26
- **pattern-recognition-specialist**: P3 — inconsistent with all other error imports

**Locations:**
- `research_agent/agent.py:26` — existing errors import
- `research_agent/agent.py:239` — lazy import inside method
- `research_agent/agent.py:327` — `_SynthesisError` usage
- `research_agent/agent.py:861` — redundant status reset

## Proposed Solutions

### Option A: Add to module imports, remove redundant line (Recommended)
1. Add `SynthesisError` to the import at line 26
2. Remove the lazy import at line 239
3. Replace `_SynthesisError` with `SynthesisError` at line 327
4. Remove redundant `self._iteration_status = "skipped"` at line 861

- **Effort:** Small
- **Risk:** None

## Acceptance Criteria

- [ ] `SynthesisError` imported at module level
- [ ] Lazy import removed from `_run_iteration()`
- [ ] Redundant status reset removed
