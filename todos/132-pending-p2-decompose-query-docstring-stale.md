---
status: resolved
priority: p2
issue_id: "132"
tags: [code-review, documentation, cycle-31]
dependencies: []
unblocks: []
sub_priority: 1
---

# 132 - decompose_query docstring missing temperature and novelty_queries params

## Problem Statement

The `decompose_query` docstring's `Args:` section lists `client`, `query`, `context_content`, `model`, and `critique_guidance`, but omits `temperature` (added in Cycle 27) and `novelty_queries` (added in Cycle 31). Since the function signature was modified in this PR, the docstring should be updated to match.

## Findings

- **Source:** kieran-python-reviewer, pattern-recognition-specialist (2 agents flagged independently)
- **Location:** `research_agent/decompose.py:82-99`
- **Convention:** CLAUDE.md says "Type hints on public function signatures" -- `decompose_query` is a public function

## Proposed Solution

Add two entries to the Args section:

```python
        temperature: Sampling temperature for the API call (0.0-1.0, default 1.0)
        novelty_queries: How many sub-queries to frame for novelty angles (0=none, max=3)
```

- **Effort:** Small (2 lines)
- **Risk:** None

## Acceptance Criteria

- [ ] `decompose_query` docstring lists all 7 parameters
- [ ] All tests still pass
