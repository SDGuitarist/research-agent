---
status: pending
priority: p3
issue_id: "050"
tags: [code-review, quality]
dependencies: []
---

# P3: Mixed f-string vs %-style logging in coverage.py

## Problem Statement

`coverage.py` uses f-strings in logger calls at lines 71, 87, 99, 152, 158 but %-style at lines 302, 309. Within one module, this looks inconsistent. f-strings eagerly evaluate even when the log level is disabled; %-style defers evaluation.

## Findings

- Flagged by: pattern-recognition-specialist, kieran-python-reviewer
- The codebase as a whole is split, but within coverage.py the inconsistency is glaring

## Proposed Solutions

Convert the 5 f-string logger calls to %-style to match the API-level logging in the same file.
- Effort: Small
- Risk: None

## Technical Details

- **File:** `research_agent/coverage.py:71, 87, 99, 152, 158`

## Acceptance Criteria

- [ ] All logger calls in coverage.py use %-style formatting
- [ ] All tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-25 | Created from review | — |
