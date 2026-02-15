---
status: ready
priority: p3
issue_id: "033"
tags: [code-review, quality, dead-code]
dependencies: []
---

# ~387 LOC Dead Code

## Problem Statement

Code simplicity review identified ~387 lines of dead/unreachable code across gap management utilities and over-engineered abstractions. Includes `detect_cycles`, `sort_gaps`, `SortedGaps` (135 LOC), `validate_gaps` (68 LOC), `update_gap` (48 LOC), and unused exception subclasses (13 LOC).

## Findings

- **Source:** Code Simplicity Reviewer agent
- **Location:** `research_agent/schema.py`, `research_agent/state.py`, `research_agent/context_result.py`, `research_agent/errors.py`
- **Note:** Related to previously rejected todo 004 (dead-code). This is a broader finding covering more modules.

## Proposed Solutions

### Option A: Remove in phases (Recommended)
Phase 1: Remove clearly dead functions (detect_cycles, sort_gaps, SortedGaps).
Phase 2: Simplify ContextResult, remove unused exceptions.
- **Effort:** Medium (1-2 hours)

## Acceptance Criteria

- [ ] Dead functions removed
- [ ] No remaining callers for removed code
- [ ] All tests pass
