# Data Integrity Guardian — Review Findings

**PR:** P3 "Do Now" Fixes
**Branch:** main (direct commits)
**Date:** 2026-02-23
**Agent:** data-integrity-guardian

## Findings

### Bool-as-int pattern also exists in schema.py
- **Severity:** P3
- **File:** research_agent/schema.py:94
- **Issue:** The `priority` field validation uses `isinstance(priority, int)` without a bool guard, same pattern as the bug fixed in context.py. `priority: true` in YAML would pass as integer 1.
- **Suggestion:** Add `isinstance(priority, bool)` check before the int check, matching the fix in context.py. Address in a future session.

### Missing test for False as score value
- **Severity:** P3
- **File:** tests/test_context.py
- **Issue:** The new test covers `True` but not `False`. While `False` (int 0) would fail the range check `1 <= 0 <= 5`, an explicit test documents the intent and guards against future range changes.
- **Suggestion:** Add `test_bool_false_rejected_as_score` in a future session.

### Removed double-sanitization actually fixes a latent encoding bug
- **Severity:** P3 (positive finding)
- **File:** research_agent/decompose.py:141, research_agent/relevance.py:122
- **Issue:** `sanitize_content` is NOT idempotent — calling it twice turns `&amp;` into `&amp;amp;`. The removed calls were causing double-encoding. This fix is correct.
- **Suggestion:** No action needed. The fix improves data correctness.

### score_source is public but now relies on caller to sanitize query
- **Severity:** P3
- **File:** research_agent/relevance.py:122
- **Issue:** `score_source` is a module-level function that now expects pre-sanitized `query`. If a future caller invokes it directly without sanitizing, unsanitized content enters the prompt. A comment documents this contract.
- **Suggestion:** Consider making it `_score_source` or adding a docstring note in a future session.

## Summary
- P1 (Critical): 0
- P2 (Important): 0
- P3 (Nice-to-have): 4 (1 positive)
