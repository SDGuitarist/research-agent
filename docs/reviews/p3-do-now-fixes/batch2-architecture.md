# Architecture Strategist — Review Findings

**PR:** P3 "Do Now" Fixes (#25, #26, #28, #29, #30)
**Branch:** main (direct commits)
**Date:** 2026-02-23
**Agent:** architecture-strategist

## Findings

### Defensive sanitization removal weakens three-layer defense
- **Severity:** P2
- **File:** research_agent/decompose.py:141-146, research_agent/relevance.py:134-137
- **Issue:** Removing `sanitize_content()` at consumer sites relies on implicit contract that producer (context.py:225) always sanitizes. Future code paths could bypass this. The three-layer defense model (sanitize + XML boundaries + system prompt) is weakened to single-point enforcement for `critique_guidance`. Cost of redundant sanitization is negligible (three `str.replace` calls on a short string).
- **Suggestion:** Restore `sanitize_content()` calls at consumer sites to maintain defense-in-depth, OR add docstring contracts and rename parameter to `sanitized_critique_guidance` to signal the precondition.

### score_source is public but has undocumented preconditions
- **Severity:** P3
- **File:** research_agent/relevance.py:108
- **Issue:** `score_source` is not underscore-prefixed but now requires pre-sanitized query input. Only called from `evaluate_sources`, but accessible as a public function.
- **Suggestion:** Consider renaming to `_score_source` to signal it's internal with preconditions.

### Document sanitization contract on _summarize_patterns
- **Severity:** P3
- **File:** research_agent/context.py:171
- **Issue:** `_summarize_patterns` return value is used directly in prompts. No docstring note about sanitization guarantee. Future refactoring could accidentally remove the final `sanitize_content()` at line 225.
- **Suggestion:** Add docstring note stating return value is used in prompts and must remain sanitized.

### String-based mode dispatch (pre-existing)
- **Severity:** P3
- **File:** research_agent/agent.py:146, 203, 208, 215, 458, 480
- **Issue:** Mode identity checked via string comparison (`self.mode.name != "quick"`) in 6 places. Pre-existing pattern, not introduced by these commits. New commit adds another instance.
- **Suggestion:** Future improvement: boolean properties on ResearchMode (e.g., `mode.has_critique`).

## Summary
- P1 (Critical): 0
- P2 (Important): 1
- P3 (Nice-to-have): 3
