---
title: "P2 Fix Batch: Redundant Re-evaluation & Query Validation Duplication"
date: 2026-02-25
category: performance-issues
tags:
  - code-review
  - performance-optimization
  - refactoring
  - code-quality
components:
  - research_agent/agent.py
  - research_agent/relevance.py
  - research_agent/coverage.py
  - research_agent/decompose.py
  - research_agent/query_validation.py
severity: medium
symptoms: |
  #046: Retry evaluation re-scored existing summaries alongside new ones, causing redundant Claude API calls per retry.
  #048: Query validation logic duplicated across coverage.py and decompose.py (~50 lines), with stop-words set recreated on every call in decompose.py.
root_cause: |
  #046: _try_coverage_retry() called evaluate_sources() on combined list instead of only new summaries; existing scores from initial evaluation ignored.
  #048: Structural duplication of strip/word-count/overlap/dedup/truncate pattern; thresholds slightly different per module discouraging initial extraction.
resolution_type:
  - code-fix
  - refactor
commits:
  - hash: a8c4ae2
    message: "fix(review): score only new summaries during retry (#046)"
  - hash: dccaa4a
    message: "refactor(review): extract shared query validation (#048)"
test_status: "All 694 tests pass"
related:
  - docs/solutions/performance-issues/adaptive-batch-backoff.md
  - docs/solutions/logic-errors/source-level-relevance-aggregation.md
  - docs/solutions/architecture/gap-aware-research-loop.md
  - LESSONS_LEARNED.md (Section 17 — Sub-Query Divergence)
---

# P2 Fix Batch: Redundant Re-evaluation & Query Validation Duplication

## Fix #046 — Retry Re-Scores Existing Summaries

### Problem

When `_try_coverage_retry` fetched new sources after a coverage gap, it passed the **combined list** (existing + new summaries) into `evaluate_sources`. Every already-scored source was sent to the LLM again for re-scoring — wasting API calls and discarding accurate prior judgments.

```python
# Before: re-scored everything
combined = existing_summaries + new_summaries
new_eval = await evaluate_sources(query=query, summaries=combined, ...)
```

### Root Cause

The retry path was written as "gather more and re-run the whole evaluation." There was no design for incremental evaluation. As retry matured (parallel search, mode-scoped source counts), that assumption became an active performance bug.

### Solution

**Score only new summaries, then merge evaluations arithmetically.**

```python
# Score ONLY new summaries
retry_eval = await evaluate_sources(
    query=query, summaries=new_summaries, ...
)

# Merge surviving/dropped from original + retry
merged_surviving = evaluation.surviving_sources + retry_eval.surviving_sources
merged_dropped = evaluation.dropped_sources + retry_eval.dropped_sources
total_scored = evaluation.total_scored + retry_eval.total_scored
total_survived = evaluation.total_survived + retry_eval.total_survived

# Re-derive decision from mode thresholds
if total_survived >= mode.min_sources_full_report:
    decision = "full_report"
elif total_survived >= mode.min_sources_short_report:
    decision = "short_report"
elif total_scored > 0 and total_survived == 0:
    decision = "no_new_findings"
else:
    decision = "insufficient_data"
```

### Verification

Test `test_retry_returns_combined_summaries_on_success` was rewritten to exercise the merge path:
- Original: 3 survivors (`short_report`, standard mode needs 4 for full)
- Retry: 1 new survivor
- Merged: 4 survived = `full_report` — verified the upgrade comes from merge arithmetic, not re-scoring

**Files:** `research_agent/agent.py`, `tests/test_agent.py`

---

## Fix #048 — Duplicated Query Validation Logic

### Problem

Identical 5-step validation existed in two modules with no shared source of truth:

| Step | `coverage.py` | `decompose.py` |
|------|--------------|-----------------|
| Strip formatting | `strip('"').strip("'").strip("-")` | Same + `strip("•")` |
| Word count bounds | `MIN_RETRY_QUERY_WORDS` / `MAX_RETRY_QUERY_WORDS` | `MIN_SUB_QUERY_WORDS` / `MAX_SUB_QUERY_WORDS` |
| Stop words | Module-level `frozenset` | Inline `set` per call |
| Reference overlap | 0.8 vs tried queries | 0.8 vs original + require overlap |
| Near-duplicate check | 0.7 threshold | 0.7 threshold |

~50 lines of structural duplication. Any threshold change required parallel edits.

### Root Cause

The two functions were written independently at different times. The structural pattern was identical, but context differed enough (retry vs sub-query, different thresholds) that duplication wasn't initially obvious.

### Solution

Created `research_agent/query_validation.py` with configurable shared utilities:

```python
STOP_WORDS: frozenset           # Single source of truth
strip_query(text, extra_chars)  # Configurable stripping
meaningful_words(text)          # Lowercase + stop word removal
has_near_duplicate(words, valid_list, threshold)
validate_query_list(            # Full pipeline with kwargs
    queries, *, min_words, max_words, max_results,
    reference_queries, max_reference_overlap,
    require_reference_overlap, dedup_threshold,
    extra_strip_chars, label,
)
```

Both callers became thin delegations:

```python
# coverage.py — 8 lines (was 45)
def _validate_retry_queries(queries, tried_queries=None):
    return validate_query_list(
        queries, min_words=MIN_RETRY_QUERY_WORDS, max_words=MAX_RETRY_QUERY_WORDS,
        max_results=MAX_RETRY_QUERIES, reference_queries=tried_queries,
        max_reference_overlap=0.8, label="Retry query",
    )

# decompose.py — 12 lines (was 45), preserves fallback to original_query
def _validate_sub_queries(sub_queries, original_query):
    validated = validate_query_list(
        sub_queries, min_words=MIN_SUB_QUERY_WORDS, max_words=MAX_SUB_QUERY_WORDS,
        max_results=MAX_SUB_QUERIES, reference_queries=[original_query],
        max_reference_overlap=MAX_OVERLAP_WITH_ORIGINAL,
        require_reference_overlap=True, extra_strip_chars="•", label="Sub-query",
    )
    if not validated:
        logger.warning("All sub-queries failed validation, using original query")
        return [original_query]
    return validated
```

### Verification

No behavioral change intended. All 88 existing tests for both modules passed without modification — they test the output contract (which queries pass/fail), not internal implementation.

**Files:** `research_agent/query_validation.py` (new), `research_agent/coverage.py`, `research_agent/decompose.py`

---

## Risk Resolution

| Phase | Risk Flagged | What Happened | Lesson |
|-------|-------------|---------------|--------|
| Review | "Interaction between retry and gap state system" | P1 fixes (#043, #044) prevented quick mode from entering retry. Deeper concern deferred. | Scope fix batches tightly — address what you can, defer what you can't. |
| Work (P2) | "Duplicated decision logic in retry merge path" | #046 inlined threshold checks from `evaluate_sources` into the merge path (~10 lines). Works correctly but creates a maintenance coupling. | Decision logic duplication is a red flag even when the fix is safe. Extract before a third copy appears. |
| Work (P2) | "Query validation duplication" | #048 eliminated it completely via `query_validation.py`. | Structural duplication (same pipeline shape, different thresholds) signals a shared utility module. Extract immediately. |

### Remaining Risk

The inline decision logic in `_try_coverage_retry` (agent.py lines 493-506) duplicates threshold comparisons from `evaluate_sources` (relevance.py lines 328-353). If thresholds change or new decision branches are added, both must be updated.

**Recommended future refactor:** Extract `_make_decision(total_survived, total_scored, mode)` in `relevance.py` and import from both call sites.

---

## Prevention Strategies

### When Adding Pipeline Stages

1. **Check for existing similar logic first:** `grep -r "decision\|validate\|filter" research_agent/`
2. **Extract shared logic early** — don't wait for the third copy
3. **Parameterize thresholds** — all magic numbers become function arguments
4. **Test both paths** — if logic appears in two execution flows (main + retry), test both

### When Adding Validation Logic

1. **Centralize constants** — `STOP_WORDS`, thresholds in one module
2. **Use keyword-only parameters** (`*`) to prevent positional argument mistakes
3. **Test the shared module first**, then integration with callers
4. **Name shared modules clearly** — `query_validation.py`, not `utils.py`

### Duplication Detection Checklist

- [ ] `grep` for similar function names across modules
- [ ] Compare function signatures — same shape = candidate for extraction
- [ ] Check constants — duplicated `frozenset`/`set` definitions are a smell
- [ ] After refactoring, verify test count unchanged (silent drops signal name corruption — see LESSONS_LEARNED Section 16)

---

## Three Questions

1. **Hardest pattern to extract from the fixes?** The decision logic duplication in #046. It's clearly a problem, but extracting `_make_decision()` as part of this compound phase would be scope creep — the fix works, the risk is documented, and the refactor is a clean future task.

2. **What did you consider documenting but left out, and why?** Considered documenting the full `validate_query_list` API design rationale (why keyword-only args, why `require_reference_overlap` vs separate function). Left it out because the function's docstring already covers this and duplicating it in solutions/ would create another sync point.

3. **What might future sessions miss that this solution doesn't cover?** The interaction between the merged evaluation's decision and `_update_gap_states` in the orchestrator. If a retry merge produces `full_report` from two `insufficient_data` evaluations, gaps get marked as verified even though no single evaluation found enough sources. This edge case is unlikely but not tested.
