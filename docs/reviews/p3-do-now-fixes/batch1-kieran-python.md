# Kieran Python Reviewer — Review Findings

**PR:** P3 "Do Now" Fixes (#25, #26, #28, #29, #30)
**Branch:** main (direct commits)
**Date:** 2026-02-23
**Agent:** kieran-python-reviewer

## Findings

### Docstring contradicts pre-sanitization contract
- **Severity:** P2
- **File:** research_agent/relevance.py:102-121
- **Issue:** `score_source` docstring says `query: The original research query` but query is now pre-sanitized by caller. Tests pass raw strings directly to `score_source`, bypassing sanitization.
- **Suggestion:** Update docstring to: `query: The research query, pre-sanitized by the caller. Must have been passed through sanitize_content() before calling.`

### Comment references nonexistent function name
- **Severity:** P3
- **File:** research_agent/relevance.py:122
- **Issue:** Comment says `score_and_filter_sources` but the actual caller is `evaluate_sources`. No function called `score_and_filter_sources` exists in the codebase.
- **Suggestion:** Change to `# query is pre-sanitized by caller (evaluate_sources)`

### _scores recomputes on every access (info only)
- **Severity:** P3 (info)
- **File:** research_agent/critique.py:58-60
- **Issue:** `_scores` rebuilds the tuple on every property access. `functools.cached_property` would be natural but doesn't work with `frozen=True` dataclasses.
- **Suggestion:** No action needed — current approach is correct given constraints.

## Summary
- P1 (Critical): 0
- P2 (Important): 1
- P3 (Nice-to-have): 2 (1 info-only)
