---
status: done
priority: p2
issue_id: "082"
tags: [code-review, quality, python]
dependencies: []
unblocks: []
sub_priority: 6
---

# P2: Bare `list` type hint on `_parse_sections` parameter

## Problem Statement

`_parse_sections(raw_sections: list)` uses a bare `list` type hint. Since the function expects a list of single-key dicts, a more informative annotation would be `list[dict[str, str]]`.

## Findings

- Flagged by: kieran-python-reviewer (P2-3)
- Project convention: type hints on public function signatures

## Proposed Solutions

### Option A: Add parameterized type hint (Recommended)

```python
def _parse_sections(raw_sections: list[dict[str, str]]) -> tuple[tuple[str, str], ...]:
```

- **Effort:** Small (1 line change)
- **Risk:** None

## Technical Details

**Affected files:**
- `research_agent/context.py` line 21

## Acceptance Criteria

- [ ] Type hint is parameterized
- [ ] mypy/pyright (if configured) passes

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-27 | Created from code review | Flagged by Python Reviewer |
