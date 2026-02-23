# Code Simplicity Reviewer — Review Findings

**PR:** P3 "Do Now" Fixes (#25, #26, #28, #29, #30)
**Branch:** main (direct commits)
**Date:** 2026-02-23
**Agent:** code-simplicity-reviewer

## Findings

### Inconsistent sanitization convention across modules
- **Severity:** P2
- **File:** research_agent/decompose.py:141, research_agent/relevance.py:136, research_agent/synthesize.py:413,497
- **Issue:** `decompose.py` and `relevance.py` now trust caller to pre-sanitize `critique_guidance`, but `synthesize.py` still double-sanitizes it. Creates inconsistent convention: trust-caller vs sanitize-at-use. A future developer adding a second caller to `decompose_query` wouldn't know to sanitize first.
- **Suggestion:** Pick one convention and apply uniformly. Cheapest fix: add comments in decompose.py and relevance.py documenting the pre-sanitized contract. More principled: decide whether "sanitize at source" or "sanitize at point of use" is the project convention.

### Missing comment in decompose.py for pre-sanitized contract
- **Severity:** P2
- **File:** research_agent/decompose.py:141
- **Issue:** `relevance.py:122` has a comment documenting the pre-sanitized assumption, but `decompose.py` has no such comment. Reader must trace call chain to verify safety.
- **Suggestion:** Add `# critique_guidance is pre-sanitized by load_critique_history` above line 141.

### Misleading variable name after sanitize removal
- **Severity:** P3
- **File:** research_agent/relevance.py:136
- **Issue:** Variable still named `safe_adjustments` but no sanitization happens at this call site anymore — only truncation.
- **Suggestion:** Rename to `adjustments` or add a comment explaining the name.

## Summary
- P1 (Critical): 0
- P2 (Important): 2
- P3 (Nice-to-have): 1
