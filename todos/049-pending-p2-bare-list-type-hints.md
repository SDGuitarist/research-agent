---
status: done
priority: p2
issue_id: "049"
tags: [code-review, quality, python]
dependencies: []
---

# P2: Bare `list` type hints on agent.py methods

## Problem Statement

Several methods in `agent.py` use bare `list` instead of `list[Summary]`:
- `_try_coverage_retry(existing_summaries: list, ...) -> tuple[list, ...] | None` (line 421)
- `_evaluate_and_synthesize(summaries: list, ...) -> str` (line 506)
- `_fetch_extract_summarize(...) -> list` (line 336)

The CLAUDE.md convention says "Type hints on public function signatures." While these are private methods, they are complex enough to warrant precise types.

## Findings

- Flagged by: kieran-python-reviewer

## Proposed Solutions

Fix type hints to `list[Summary]`.
- Effort: Small (3 signatures)
- Risk: None

## Technical Details

- **File:** `research_agent/agent.py:336, 421, 506`

## Acceptance Criteria

- [ ] All three methods use `list[Summary]` instead of bare `list`
- [ ] All tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-25 | Created from review | — |
