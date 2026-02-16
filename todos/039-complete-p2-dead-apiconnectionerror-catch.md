---
status: complete
priority: p2
issue_id: "039"
tags: [code-review, quality]
dependencies: []
---

# Dead Code: APIConnectionError in Final Catch Clause

## Problem Statement

`APIConnectionError` is a subclass of `APIError` (hierarchy: `APITimeoutError → APIConnectionError → APIError`). The `except APIError` handler catches it before the final clause ever runs, making `APIConnectionError` in the final `except` tuple unreachable dead code at all 3 locations in `synthesize.py`.

## Findings

- **kieran-python-reviewer**: Confirmed via SDK MRO that `APIConnectionError` inherits from `APIError`. The catch is dead code at lines 235, 338, 553.
- **security-sentinel**: Independently confirmed the same hierarchy.
- **pattern-recognition-specialist**: Confirmed the issue.

## Proposed Solutions

### Option A: Remove APIConnectionError from final catch (Recommended)
- **Pros**: Eliminates dead code, reduces false sense of coverage
- **Cons**: None
- **Effort**: Small (3 lines)
- **Risk**: None — removing unreachable code

## Technical Details

- **Affected files**: `research_agent/synthesize.py` (lines 235, 338, 553)
- **Also**: Remove `APIConnectionError` from import on line 10

## Acceptance Criteria

- [ ] `APIConnectionError` removed from all 3 final catch clauses
- [ ] `APIConnectionError` removed from imports
- [ ] All 527 tests pass
