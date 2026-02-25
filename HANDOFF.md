# Handoff: Research Agent — P2 Fix Batch

## Current State

**Project:** Research Agent — Cycle 21 coverage gap P2 fixes
**Phase:** FIX COMPLETE (P1 + P2)
**Branch:** `main`
**Date:** February 25, 2026

---

## Prior Phase Risk

> "Least confident about going into the next batch or compound phase? The HANDOFF.md diff is large because it replaced the previous session's content. No code concern — the fixes are minimal and well-tested."

Accepted: No code risk to address. Proceeding with P2 fixes.

## What Was Done This Session

### Previously committed (from prior session)

1. **Fixed #045** — Refactored sequential retry searches to use `_search_sub_queries` for parallel execution.
2. **Fixed #047** — Moved `RETRY_SOURCES_PER_QUERY` from module constant to per-mode config (quick=2, standard=3, deep=5). Added `Summary` type hints.

**Commit:** `1d60c4d` — `fix(review): parallel retry search + mode-scoped retry config (#045, #047)`

### This session

3. **Fixed #046** — Retry no longer re-scores existing summaries. `_try_coverage_retry` now calls `evaluate_sources` on only `new_summaries`, then merges surviving/dropped from both evaluations and computes the combined decision using mode thresholds. Updated test to verify merge upgrades `short_report` → `full_report`.

**Commit:** `a8c4ae2` — `fix(review): score only new summaries during retry (#046)`

4. **Fixed #048** — Extracted shared query validation into `research_agent/query_validation.py` with `STOP_WORDS`, `strip_query()`, `meaningful_words()`, `has_near_duplicate()`, and `validate_query_list()`. Both `coverage.py` and `decompose.py` now delegate to it, eliminating ~50 lines of duplicated logic.

**Commit:** `dccaa4a` — `refactor(review): extract shared query validation (#048)`

5. **All 694 tests pass** across all commits.

### P2 status

| Todo | Description | Status |
|------|-------------|--------|
| #045 | Sequential retry searches | Done |
| #046 | Redundant re-evaluation | Done |
| #047 | Retry sources in mode | Done |
| #048 | Query validation duplication | Done |
| #049 | Bare list type hints | Pending (cosmetic) |

## Three Questions

1. **Hardest fix in this batch?** #046 — scoring only new summaries required duplicating the decision logic from `evaluate_sources` into the retry merge path. Considered extracting a `_make_decision()` helper in `relevance.py`, but that would be a refactor beyond the fix scope. The inline decision is ~10 lines and self-contained.

2. **What did you consider fixing differently, and why didn't you?** For #048, considered Option B (sharing only `_STOP_WORDS` without extracting validation). Went with Option A because the structural duplication (strip → word count → overlap → dedup → truncate) was identical and the thresholds are now configurable via `validate_query_list()` parameters.

3. **Least confident about going into the next batch or compound phase?** The duplicated decision logic in `_try_coverage_retry` (agent.py) — if `evaluate_sources` decision thresholds change, the retry merge path must be updated too. A future refactor could extract `_make_decision()` to keep them in sync.

## Next Phase

**COMPOUND** — Document P1+P2 learnings in `docs/solutions/`. Then consider P3 items (#050-#053) or review.

### Prompt for Next Session

```
Read HANDOFF.md. Run /workflows:compound to document P1+P2 fix batch learnings in docs/solutions/. Focus on: retry evaluation merge pattern, shared query validation extraction, and the decision-logic duplication risk flagged in Three Questions. Then stop.
```
