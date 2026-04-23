---
status: resolved
priority: p2
issue_id: "134"
tags: [code-review, testing, invariant, cycle-31]
dependencies: []
unblocks: []
sub_priority: 3
---

# 134 - Cross-module invariant test for novelty_queries upper bound vs MAX_SUB_QUERIES

## Problem Statement

`modes.py:90` validates `novelty_queries` against hardcoded `3` with a comment "Must match decompose.MAX_SUB_QUERIES". This is comment-enforced coupling -- if MAX_SUB_QUERIES changes in decompose.py, the validation silently drifts. Importing directly would create a circular dependency (modes.py -> decompose.py, but decompose.py already imports from modes.py indirectly).

## Findings

- **Source:** kieran-python-reviewer, architecture-strategist, pattern-recognition-specialist (3 agents flagged)
- **Location:** `research_agent/modes.py:89-91`, `research_agent/decompose.py:16`
- **Root cause:** Circular import prevents direct constant sharing

## Proposed Solution

Add a cross-module assertion test in `tests/test_modes.py`:

```python
def test_novelty_queries_upper_bound_matches_max_sub_queries():
    """Ensure modes.py validation stays in sync with decompose.MAX_SUB_QUERIES."""
    from research_agent.decompose import MAX_SUB_QUERIES
    from research_agent.modes import ResearchMode
    # The deep mode has the highest novelty_queries value
    assert ResearchMode.deep().novelty_queries <= MAX_SUB_QUERIES
```

This makes the coupling machine-enforced at test time without introducing circular imports.

- **Effort:** Small (1 test, ~5 lines)
- **Risk:** None

## Acceptance Criteria

- [ ] Test exists that will fail if MAX_SUB_QUERIES < deep mode's novelty_queries
- [ ] All tests pass
