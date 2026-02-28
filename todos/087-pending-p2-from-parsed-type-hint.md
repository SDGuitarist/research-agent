---
status: pending
priority: p2
issue_id: "087"
tags: [code-review, quality, type-safety]
dependencies: []
unblocks: []
sub_priority: 2
---

# P2: `from_parsed` type hint `dict[str, int]` is inaccurate

## Problem Statement

`CritiqueResult.from_parsed(parsed: dict[str, int], ...)` declares the `parsed` parameter as `dict[str, int]`, but the actual dict from `_parse_critique_response()` contains both `int` values (5 dimension scores) and `str` values (`weaknesses`, `suggestions`). The classmethod only reads DIMENSIONS keys (which are ints), so it works correctly at runtime, but the type annotation is misleading and would cause false alarms if type checking is ever enabled.

## Findings

- Flagged by: architecture-strategist (P2), pattern-recognition-specialist (P3), kieran-python-reviewer (P3)
- 3/6 agents independently flagged this — consensus finding
- `critique.py` line 59: `def from_parsed(cls, parsed: dict[str, int], ...)`
- `_parse_critique_response` (line 96) returns `dict[str, int | str]`
- Plan specified `dict[str, int]` as "tightened type hint" — but this was based on the intent (only scores matter), not the actual data shape flowing through

## Proposed Solutions

### Option A: Widen to `dict[str, int | str]` (Recommended)
- Accurately reflects the actual input from `_parse_critique_response`
- One-line change
- **Effort:** Small (1 line)
- **Risk:** None

### Option B: `dict[str, Any]`
- More permissive, less informative
- **Effort:** Small (1 line)
- **Risk:** None, but loses type information

## Technical Details

**Affected files:**
- `research_agent/critique.py` line 59

## Acceptance Criteria

- [ ] Type hint accurately reflects the dict shape from `_parse_critique_response`
- [ ] All tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-28 | Created from P2 triage review | 3/6 agents flagged independently |
