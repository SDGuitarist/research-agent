---
status: done
priority: p2
issue_id: "048"
tags: [code-review, architecture, quality]
dependencies: []
---

# P2: Duplicated query validation logic between coverage.py and decompose.py

## Problem Statement

`_validate_retry_queries()` in `coverage.py:56-107` and `_validate_sub_queries()` in `decompose.py:34-98` share ~30 lines of structurally identical code: strip formatting, word count validation, stop-word-filtered overlap comparison, near-duplicate detection, and max-count truncation. The `_STOP_WORDS` set is also duplicated (as a `frozenset` in coverage.py and an inline `set` recreated per-call in decompose.py).

## Findings

- Flagged by: pattern-recognition-specialist
- Both use the same overlap-checking pattern with slightly different thresholds (0.8 vs 0.8 for tried queries, 0.7 for internal dedup)
- decompose.py recreates the stop words set on every call (minor perf issue)

## Proposed Solutions

### Option A: Extract shared `validate_query_list()` helper (Recommended)
Create `research_agent/query_validation.py` with configurable thresholds, stop words, and reference queries.
- Pros: Eliminates ~50 lines of duplication, ensures threshold changes stay in sync
- Cons: New module to maintain
- Effort: Medium
- Risk: Low

### Option B: Share only the stop words
Move `_STOP_WORDS` to a common location, keep validation separate.
- Pros: Minimal change
- Cons: Structural duplication remains
- Effort: Small
- Risk: None

## Technical Details

- **Files:** `research_agent/coverage.py:50-107`, `research_agent/decompose.py:34-98`

## Acceptance Criteria

- [ ] No duplicated validation logic between coverage.py and decompose.py
- [ ] Stop words defined once, shared
- [ ] All tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-25 | Created from review | — |
