---
status: complete
priority: p1
issue_id: "100"
tags: [code-review, quality, documentation]
dependencies: []
unblocks: []
sub_priority: 1
---

# Missing `skip_iteration` in `run_research()` docstring

## Problem Statement

The `skip_iteration` parameter exists in the function signature of `run_research()` and `run_research_async()` in `__init__.py` but is missing from the `Args:` docstring. This is the public API surface — callers reading docs won't discover the parameter.

## Findings

- **kieran-python-reviewer**: P1 — public API documentation gap
- **architecture-strategist**: Confirmed — docstring at line 55 lists `skip_critique` but not `skip_iteration`
- **agent-native-reviewer**: Confirmed — Python API users won't know this exists

**Location:** `research_agent/__init__.py:49-55`

## Proposed Solutions

### Option A: Add to docstring (Recommended)
Add `skip_iteration: If True, skip post-report query refinement and follow-up questions.` to the Args section.

- **Pros:** Quick fix, consistent with other params
- **Cons:** None
- **Effort:** Small
- **Risk:** None

## Acceptance Criteria

- [ ] `skip_iteration` documented in `run_research()` Args section
- [ ] Matches the format of `skip_critique` documentation
