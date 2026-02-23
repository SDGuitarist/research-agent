# Security Sentinel — Review Findings

**PR:** P3 "Do Now" Fixes (#25, #26, #28, #29, #30)
**Branch:** main (direct commits)
**Date:** 2026-02-23
**Agent:** security-sentinel

## Findings

### Sanitize-at-producer creates fragile invariant + inconsistent convention
- **Severity:** P3
- **File:** research_agent/decompose.py:141-146, research_agent/relevance.py:122,135-136, research_agent/synthesize.py:413,497
- **Issue:** After removing sanitization from decompose.py and relevance.py, the convention is now inconsistent: two consumers trust the producer, one (synthesize.py) still double-sanitizes. A future developer reading synthesize.py would assume sanitization is the consumer's job; reading decompose.py would assume it's the producer's job. Additionally, `sanitize_content()` is NOT idempotent — double-sanitization produces `&amp;amp;` from `&amp;`. If weakness strings contain ampersands (e.g., "R&D sources lacking"), synthesize.py would double-encode them.
- **Suggestion:** Pick one convention: (A) Sanitize at consumer (re-add calls in decompose.py and relevance.py, remove from context.py:225) OR (B) Sanitize at producer only (also remove from synthesize.py:413,497). Option A is recommended per the project's three-layer defense philosophy.

### No critical vulnerabilities found
- **Severity:** Info
- **File:** N/A
- **Issue:** Bool type guard (context.py:153) is a correctness fix, not security. Quick mode guard has no security impact. _scores extraction has no security impact. The data source for critique_guidance (local YAML files written by the agent) limits attack surface.
- **Suggestion:** N/A

## Summary
- P1 (Critical): 0
- P2 (Important): 0
- P3 (Nice-to-have): 1
