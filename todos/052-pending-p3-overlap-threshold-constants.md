---
status: pending
priority: p3
issue_id: "052"
tags: [code-review, quality]
dependencies: []
---

# P3: Magic number overlap thresholds should be named constants

## Problem Statement

`coverage.py:86` uses `0.8` and line 98 uses `0.7` for overlap thresholds inline. `decompose.py` extracts its equivalent as `MAX_OVERLAP_WITH_ORIGINAL = 0.8`. The coverage module should do the same for consistency and readability.

## Findings

- Flagged by: pattern-recognition-specialist, code-simplicity-reviewer
- Simplicity reviewer suggests merging to a single threshold (0.8) — the 0.7 vs 0.8 distinction is hard to justify

## Proposed Solutions

Extract as named constants: `_TRIED_OVERLAP_THRESHOLD = 0.8` and `_INTERNAL_OVERLAP_THRESHOLD = 0.7` (or merge to single `_OVERLAP_THRESHOLD = 0.8`).
- Effort: Trivial
- Risk: None

## Technical Details

- **File:** `research_agent/coverage.py:86, 98`

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-25 | Created from review | — |
