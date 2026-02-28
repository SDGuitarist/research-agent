---
status: done
priority: p1
issue_id: "044"
tags: [code-review, quality, python]
dependencies: []
---

# P1: `_parse_gap_response` type hint lies about accepting `None`

## Problem Statement

`_parse_gap_response(text: str, ...)` declares `text: str` but handles `None` at runtime (line 118: `if not text or not text.strip()`). A test `test_none_returns_safe_default` confirms this behavior. The type hint is a lie to static analysis tools — mypy/pyright would flag calling this with `None` as an error.

## Findings

- Flagged by: kieran-python-reviewer
- The function is called from `identify_coverage_gaps` which passes `response.content[0].text.strip()` — always a `str`
- However, the defensive handling of `None` is appropriate for a parser of LLM output

## Proposed Solutions

### Option A: Fix type hint to `str | None` (Recommended)
- Pros: Matches actual behavior, honest contract
- Cons: None
- Effort: Trivial (1 line)
- Risk: None

## Technical Details

- **File:** `research_agent/coverage.py:110`

## Acceptance Criteria

- [ ] `_parse_gap_response` signature is `text: str | None`
- [ ] All tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-25 | Created from review | — |
