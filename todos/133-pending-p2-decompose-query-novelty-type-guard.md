---
status: resolved
priority: p2
issue_id: "133"
tags: [code-review, security, defense-in-depth, cycle-31]
dependencies: []
unblocks: []
sub_priority: 2
---

# 133 - decompose_query missing runtime type guard on novelty_queries

## Problem Statement

`decompose_query(novelty_queries: int = 0)` has a type hint but no runtime validation. The value is interpolated into the system prompt via `.format(novelty_queries=novelty_queries)`. Currently the only caller validates via `ResearchMode.__post_init__`, but the function is module-level and could be called directly. A non-int value would be injected into the system prompt.

## Findings

- **Source:** security-sentinel
- **Location:** `research_agent/decompose.py:80`
- **Mitigating factors:** Internal API, single validated caller, `if novelty_queries > 0` guard would TypeError on most non-numeric types
- **Defense-in-depth principle:** Validate at the function boundary, not just at the caller

## Proposed Solution

Add an isinstance + range check at the top of the function:

```python
if not isinstance(novelty_queries, int) or not (0 <= novelty_queries <= MAX_SUB_QUERIES):
    raise ValueError(f"novelty_queries must be int 0-{MAX_SUB_QUERIES}, got {novelty_queries!r}")
```

- **Effort:** Small (2 lines)
- **Risk:** None

## Acceptance Criteria

- [ ] `decompose_query(novelty_queries="inject")` raises ValueError
- [ ] `decompose_query(novelty_queries=5)` raises ValueError
- [ ] All existing tests still pass
