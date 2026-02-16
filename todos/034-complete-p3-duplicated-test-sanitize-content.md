---
status: complete
priority: p3
issue_id: "034"
tags: [code-review, quality, duplication]
dependencies: []
---

# Duplicated TestSanitizeContent in 3 Test Files

## Problem Statement

`TestSanitizeContent` test class is duplicated across 3 test files: `test_relevance.py`, `test_synthesize.py`, and `test_summarize.py`. These are identical test classes testing the same `sanitize_content()` function.

## Findings

- **Source:** Pattern Recognition Specialist agent
- **Location:** `tests/test_relevance.py:24`, `tests/test_synthesize.py:20`, `tests/test_summarize.py:24`

## Proposed Solutions

### Option A: Keep only in test_sanitize.py (Recommended)
Remove duplicates from 3 files. Keep or create a single `TestSanitizeContent` in `tests/test_sanitize.py`.
- **Effort:** Small (15 min)

## Acceptance Criteria

- [ ] Single `TestSanitizeContent` class exists
- [ ] All tests pass
