# Performance Oracle — Review Findings

**PR:** Self-Enhancing Agent (self-critique feedback loop)
**Branch:** main (bad292e..57bf44e)
**Date:** 2026-02-23
**Agent:** performance-oracle

## Findings

### 1. Synchronous File I/O Blocks Async Event Loop
- **Severity:** P2
- **File:** research_agent/agent.py:193-195
- **Issue:** `load_critique_history(Path("reports/meta"))` performs synchronous disk I/O (glob, stat, read_text, yaml.safe_load) inside `_research_async`. With 10 files, that's ~20 blocking syscalls. Blocks the event loop.
- **Suggestion:** Wrap in `await asyncio.to_thread(load_critique_history, Path("reports/meta"))` to match pattern used elsewhere in pipeline.

### 2. Synchronous Critique API Call Blocks Event Loop
- **Severity:** P2
- **File:** research_agent/agent.py:126-156
- **Issue:** `_run_critique` calls `evaluate_report` which uses synchronous `client.messages.create()` with a 30-second timeout. Blocks event loop for up to 30 seconds. `save_critique` also performs synchronous disk I/O.
- **Suggestion:** Wrap `_run_critique` in `await asyncio.to_thread(self._run_critique, ...)` at the call site, or convert to use `async_client`.

### 3. Critique Context Not Registered in Token Budget
- **Severity:** P2
- **File:** research_agent/synthesize.py:481-490
- **Issue:** `lessons_applied` injected into prompt but not registered in `budget_components` (line 398-406). The `lessons_block` is appended without budget accounting. If critique text grows, it adds unbounded tokens that the budget pruner doesn't know about. Same applies to `scoring_adjustments` in relevance.py.
- **Suggestion:** Add `lessons_applied` to `budget_components` and `COMPONENT_PRIORITY` in `token_budget.py` at low priority (alongside `previous_baseline`).

### 4. Bare `except Exception` Masks Performance Bugs
- **Severity:** P2
- **File:** research_agent/agent.py:155-156
- **Issue:** `except (CritiqueError, Exception)` silently swallows unexpected errors. If a bug causes critique to fail on every run, no one notices — the feature silently degrades without any visible performance signal.
- **Suggestion:** Narrow exception types. Let programming errors propagate.

### 5. Double `stat()` on Critique Files During Sort
- **Severity:** P3
- **File:** research_agent/context.py:251-255
- **Issue:** Sort key `lambda p: p.stat().st_mtime` may call `stat()` more than once per file during O(n log n) sort. Trivial with 10 files but wasteful.
- **Suggestion:** Use decorate-sort-undecorate pattern to call `stat()` exactly once per file.

### 6. Unbounded Glob Before Limit Slicing
- **Severity:** P3
- **File:** research_agent/context.py:251-255
- **Issue:** `glob("critique-*.yaml")` returns all matching files, then all are stat-ed and sorted, only then sliced to `limit=10`. Directory could accumulate hundreds of files over time.
- **Suggestion:** For now acceptable. Consider periodic pruning or using filename timestamps for pre-sort.

### 7. Exact-String Weakness Counting is Ineffective
- **Severity:** P3
- **File:** research_agent/context.py:202-208
- **Issue:** `Counter` counts weaknesses by exact string match. LLM free-text outputs rarely produce identical strings across runs ("Only US sources" vs "Primarily US-based sources"). Feature silently degrades — no performance cost, but wasted opportunity.
- **Suggestion:** Consider fuzzy matching or normalized vocabulary. Or drop recurring-weakness detection and keep only dimension averages.

### 8. Hardcoded `Path("reports/meta")` in Two Places
- **Severity:** P3
- **File:** research_agent/agent.py:149, :193
- **Issue:** Relative path repeated twice, CWD-dependent. If invoked from wrong directory, both save and load silently target wrong location — feature degrades without warning.
- **Suggestion:** Extract to constant or make configurable.

### 9. Extra API Call Cost per Standard/Deep Run
- **Severity:** P3
- **File:** research_agent/critique.py:187-194
- **Issue:** One additional Claude call per run (`max_tokens=300`). ~$0.003-0.005 per call. Adds ~1-1.5% cost overhead in standard mode, <1% in deep. 30-second timeout is the main latency concern.
- **Suggestion:** Cost is acceptable. Consider reducing timeout to 15 seconds (matching `SCORING_TIMEOUT`) since the response is very short.

### 10. Redundant Sanitize Calls Across 15 Source Scorings
- **Severity:** P3
- **File:** research_agent/relevance.py:133-136
- **Issue:** `sanitize_content(scoring_adjustments)` called inside `score_source`, which runs once per source. In standard mode with 15 sources, that's 15 redundant sanitize calls on the same string.
- **Suggestion:** Pre-sanitize once in `evaluate_sources` before the per-source loop.

### 11. Quick Mode Loads Critique History Unnecessarily
- **Severity:** P3
- **File:** research_agent/agent.py:192-196
- **Issue:** `load_critique_history` called unconditionally regardless of mode. In quick mode, the loaded context is barely used (only `evaluate_sources` receives it). Disk I/O overhead is unnecessary for a speed-focused mode.
- **Suggestion:** Guard with `if self.mode.name != "quick":` before loading.

## Summary
- P1 (Critical): 0
- P2 (Important): 4
- P3 (Nice-to-have): 7
