# Pattern Recognition Specialist — Review Findings

**PR:** P3 "Do Now" Fixes (#25, #26, #28, #29, #30)
**Branch:** main (direct commits)
**Date:** 2026-02-23
**Agent:** pattern-recognition-specialist

## Findings

### Stale function name in comment
- **Severity:** P1
- **File:** research_agent/relevance.py:122
- **Issue:** Comment says `score_and_filter_sources` but the actual caller is `evaluate_sources`. No function with that name exists in the codebase.
- **Suggestion:** Change to `# query is pre-sanitized by caller (evaluate_sources)`

### String-based mode dispatch (pre-existing)
- **Severity:** P2
- **File:** research_agent/agent.py:146, 203, 208, 215, 458, 480
- **Issue:** Mode dispatch uses string comparisons (`self.mode.name == "quick"`) in 6 places. Stringly-typed anti-pattern — typos would silently fall through. New commit adds another instance at line 203.
- **Suggestion:** Future improvement: use enum (`ModeType.QUICK`) or boolean properties on `ResearchMode` (e.g., `mode.has_critique`). Not introduced by these commits, consistent with existing convention.

### Comment-based contract for pre-sanitized query
- **Severity:** P2
- **File:** research_agent/relevance.py:122
- **Issue:** Pre-sanitization contract enforced only by comment, not by type or assertion. Comment itself has wrong function name.
- **Suggestion:** Fix comment (minimum). Consider renaming parameter to `safe_query` or adding defensive assertion.

### getattr coupling between DIMENSIONS and dataclass fields
- **Severity:** P3
- **File:** research_agent/critique.py:60
- **Issue:** `getattr(self, d) for d in DIMENSIONS` couples field names to DIMENSIONS tuple at runtime. Renaming a field without updating DIMENSIONS would raise AttributeError.
- **Suggestion:** Acceptable — tests cover both properties. Frozen dataclass makes drift unlikely.

### Duplicated sanitize-then-truncate pattern (pre-existing)
- **Severity:** P3
- **File:** research_agent/critique.py:204-206, 283-285
- **Issue:** Three identical `sanitize_content(parsed.get(...))[:MAX_TEXT_LENGTH]` lines duplicated in two functions.
- **Suggestion:** Low-priority extraction. Pre-existing, not introduced by these commits.

### critique_ctx abbreviation inconsistent
- **Severity:** P3
- **File:** research_agent/agent.py:204
- **Issue:** `critique_ctx` abbreviation inconsistent with `ctx_result`/`full_result` naming pattern elsewhere.
- **Suggestion:** Cosmetic rename to `critique_result` for consistency. Not blocking.

### _scores could be more descriptive
- **Severity:** P3
- **File:** research_agent/critique.py:59
- **Issue:** `_scores` could be `_dimension_scores` for clarity. Private property on small class, intent is clear in context.
- **Suggestion:** Cosmetic, no action needed.

## Summary
- P1 (Critical): 1
- P2 (Important): 2
- P3 (Nice-to-have): 4
