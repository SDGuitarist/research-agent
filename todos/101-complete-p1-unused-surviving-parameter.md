---
status: complete
priority: p1
issue_id: "101"
tags: [code-review, quality, dead-code]
dependencies: []
unblocks: []
sub_priority: 2
---

# Unused `surviving` parameter in `_run_iteration()`

## Problem Statement

The `surviving: tuple` parameter in `_run_iteration()` is passed from the call site in `_evaluate_and_synthesize()` but never referenced inside the method body. Dead parameters confuse readers and trigger linter warnings.

## Findings

- **kieran-python-reviewer**: P1 — dead parameter, lacks type annotation
- **code-simplicity-reviewer**: Confirmed — never read, evaluation object used instead
- **pattern-recognition-specialist**: P2 — dead code, most likely to cause confusion

**Location:** `research_agent/agent.py:228-234` (signature), `agent.py:867` (call site)

## Proposed Solutions

### Option A: Remove the parameter (Recommended)
Delete `surviving: tuple` from the method signature and `surviving,` from the call site at line 867.

- **Pros:** Eliminates confusion, 2 lines removed
- **Cons:** None — `evaluation.surviving_sources` is available if needed
- **Effort:** Small
- **Risk:** None

## Acceptance Criteria

- [ ] `surviving` parameter removed from `_run_iteration()` signature
- [ ] `surviving,` removed from call site at line 867
- [ ] Tests still pass
