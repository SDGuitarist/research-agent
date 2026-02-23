# Performance Oracle — Review Findings

**PR:** P3 "Do Now" Fixes (#25, #26, #28, #29, #30)
**Branch:** main (direct commits)
**Date:** 2026-02-23
**Agent:** performance-oracle

## Findings

### Quick mode critique skip saves 10-50ms disk I/O
- **Severity:** P2 (positive improvement)
- **File:** research_agent/agent.py:202-206
- **Issue:** Positive finding. Quick mode now skips `load_critique_history` which reads up to 10 YAML files from disk. Saves glob scan + sort + file reads + YAML parsing. On cold filesystem could save 100ms+.
- **Suggestion:** No action needed — correct optimization.

### Query sanitization hoisting reduces O(N) to O(1)
- **Severity:** P2 (positive improvement)
- **File:** research_agent/relevance.py:293,303
- **Issue:** Positive finding. `sanitize_content(query)` moved from per-source (N calls) to per-batch (1 call). In deep mode with 24 source chunks, eliminates 23 redundant sanitization calls.
- **Suggestion:** No action needed — correct optimization.

### Future scalability concern: critique file glob (pre-existing)
- **Severity:** P3
- **File:** research_agent/context.py:228 (load_critique_history)
- **Issue:** `glob("critique-*.yaml")` scans all files in meta directory even though only 10 are used. At 5000 files, glob + sort becomes measurable. Pre-existing issue, not introduced by these commits.
- **Suggestion:** Future: add file-count cap or rotation to `reports/meta/`, or maintain an index file.

### _scores property recomputation is negligible
- **Severity:** P3 (info)
- **File:** research_agent/critique.py:58-60
- **Issue:** `_scores` rebuilds a 5-element tuple on every access. Called at most 2-3 times per research run. `functools.cached_property` incompatible with frozen dataclass. Cost is trivially cheap.
- **Suggestion:** No action needed.

## Summary
- P1 (Critical): 0
- P2 (Important): 2 (both positive improvements)
- P3 (Nice-to-have): 2 (1 pre-existing, 1 info)
