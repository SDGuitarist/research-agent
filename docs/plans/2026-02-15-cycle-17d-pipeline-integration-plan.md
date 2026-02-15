# Cycle 17D: Pipeline Integration — Implementation Plan

**Date:** 2026-02-15
**Cycle:** 17D (Pipeline Integration)
**Scope:** Context refactor to ContextResult, token budget enforcement, relevance gate extension to 5-way, pre/post-research hooks for gap state updates
**Inputs:** Cycles 17A-17C implementation, `cycle-17-05-cycle-breakdown.md`, `cycle-17-03-failure-modes.md`, `cycle-17-04-edge-cases.md`
**Estimated total lines:** ~190 delta (modifications to existing files only)
**Estimated commits:** 5
**New files:** 0
**Modified files:** 5 production + tests

---

## Purpose

Wire all foundation modules (17A-17C) into the existing research pipeline. This is the cycle where `agent.py`, `context.py`, `synthesize.py`, and `relevance.py` learn about schemas, budgets, and state. No new standalone modules — only integration code connecting what already exists.

After this cycle, the research agent:
- Distinguishes "missing context" from "failed to load context" from "empty context"
- Enforces token budgets before building any synthesis prompt
- Knows what it already knows (gap schema) and can skip redundant research
- Updates gap state after each research run (closing the state loop)

---

## 17A/17B/17C Foundation Used

| Component | From | How 17D Uses It |
|-----------|------|-----------------|
| `ContextResult` / `ContextStatus` | `context_result.py` (17A) | Return type for all context loaders in `context.py` |
| `allocate_budget()` / `count_tokens()` | `token_budget.py` (17A) | Budget enforcement in `synthesize.py` before prompt construction |
| `CycleConfig` | `cycle_config.py` (17A) | Accepted by `ResearchAgent.__init__()` for batch limits and budget caps |
| `load_schema()` / `sort_gaps()` | `schema.py` (17B) | Pre-research gap check in `agent.py` |
| `detect_stale()` / `select_batch()` | `staleness.py` (17C) | Pre-research staleness detection |
| `mark_verified()` / `mark_checked()` | `state.py` (17C) | Post-research gap state updates |
| `save_schema()` | `state.py` (17C) | Persisting updated gap states after research |
| `log_flip()` | `staleness.py` (17C) | Audit logging for any status changes |

---

## Build Order

```
Session 1: Context loader refactor (context.py + agent.py callers)
    ↓
Session 2: Token budget enforcement (synthesize.py + token_budget.py)
    ↓
Session 3: Relevance gate extension (relevance.py)
    ↓
Session 4: Pre-research gap check (agent.py)
    ↓
Session 5: Post-research state update (agent.py)
```

Session 1 must come first because Sessions 4-5 depend on `ContextResult` being the return type. Session 2 is independent but ordered before Session 3 because the budget enforcement must be in place before new context sources (schema data) are added to prompts. Sessions 4-5 are strictly ordered: pre-research must exist before post-research references it.

---

## Deliverable 1: Context Loader Refactor

**Files modified:** `research_agent/context.py`, `research_agent/agent.py`
**Tests modified:** `tests/test_context.py`, `tests/test_decompose.py` (4 tests), `tests/test_agent.py`
**Estimated lines:** ~30 delta (production), ~40 delta (tests)

### What changes

**`context.py` — all three loaders change return type from `str | None` to `ContextResult`:**

#### `load_full_context()` (lines 27-45)

Current:
```python
def load_full_context(context_path: Path | None = None) -> str | None:
    path = context_path or DEFAULT_CONTEXT_PATH
    try:
        if path.exists():
            content = path.read_text().strip()
            if content:
                return content
    except OSError as e:
        logger.warning(...)
    return None
```

New:
```python
def load_full_context(context_path: Path | None = None) -> ContextResult:
    path = context_path or DEFAULT_CONTEXT_PATH
    source = str(path)
    try:
        if not path.exists():
            return ContextResult.not_configured(source=source)
        content = path.read_text().strip()
        if not content:
            return ContextResult.empty(source=source)
        logger.info(f"Loaded research context from {path}")
        return ContextResult.loaded(content, source=source)
    except OSError as e:
        logger.warning(f"Could not read context file {path}: {e}")
        return ContextResult.failed(str(e), source=source)
```

Key change: four distinct return states instead of conflating all failures into `None`.

#### `load_search_context()` (lines 78-88)

Current: `if not full: return None`
New: `if not full_result: return ContextResult.not_configured(source=...)` — propagates the upstream status. When `full_result` is loaded, extracts sections and returns `ContextResult.loaded(sliced_content, source=...)`.

#### `load_synthesis_context()` (lines 90-101)

Same pattern as `load_search_context()`.

**New import in `context.py`:**
```python
from .context_result import ContextResult
```

**`agent.py` — caller updates (2 call sites):**

Line 310 changes:
```python
# Before:
business_context = load_full_context()
# After:
ctx_result = load_full_context()
business_context = ctx_result.content
```

Line 333 changes:
```python
# Before:
synthesis_context = load_synthesis_context()
# After:
synth_result = load_synthesis_context()
synthesis_context = synth_result.content
```

The downstream functions (`synthesize_report`, `synthesize_final`, `run_skeptic_combined`) already check `if business_context:` which works correctly with `str | None` from `.content`.

### Acceptance criteria

1. `load_full_context()` returns `ContextResult` with correct status for each scenario:
   - File doesn't exist → `status=NOT_CONFIGURED`
   - File exists but empty → `status=EMPTY`
   - File exists with content → `status=LOADED`
   - File read fails → `status=FAILED` with error message
2. `load_search_context()` and `load_synthesis_context()` return `ContextResult`
3. `bool(result)` is `True` only when content was successfully loaded
4. All downstream callers in `agent.py` work correctly with `.content` extraction
5. No behavioral change in the pipeline — same outputs, same degradation behavior

### Tests that WILL break (must be updated)

**`tests/test_context.py` — 14 tests affected:**

| Test class | Tests | What changes |
|------------|-------|-------------|
| `TestLoadFullContext` | 4 tests | Assert `ContextResult` instead of `str \| None`. `test_reads_file` → check `result.content`. `test_returns_none_*` → check `result.status` |
| `TestLoadSearchContext` | 4 tests | Content assertions use `result.content`. `test_returns_none_*` → check `result.status` |
| `TestLoadSynthesisContext` | 6 tests | Content assertions use `result.content`. `test_returns_none_*` → check `result.status` |

**`tests/test_decompose.py` — 4 tests in `TestLoadContext` class:**
- `test_returns_content_when_file_exists` → `assert result.content == "..."`
- `test_returns_none_when_file_missing` → `assert result.status == ContextStatus.NOT_CONFIGURED`
- `test_returns_none_for_empty_file` → `assert result.status == ContextStatus.EMPTY`
- `test_handles_os_error_gracefully` → `assert result.status == ContextStatus.FAILED`

**`tests/test_agent.py` — 13 tests that mock context loaders:**

All `mock_synth_ctx.return_value = "Business context"` must change to:
```python
mock_synth_ctx.return_value = ContextResult.loaded("Business context")
```

All `mock_load_context.return_value = "We are a guitar company."` must change to:
```python
mock_load_context.return_value = ContextResult.loaded("We are a guitar company.")
```

All `return_value=None` must change to:
```python
return_value=ContextResult.not_configured()
```

**`tests/test_synthesize.py` — 0 tests affected:**
Synthesize functions receive `business_context: str | None` from agent.py — the type hasn't changed at their interface.

### New tests

| Test | Validates |
|------|-----------|
| `test_load_full_context_returns_context_result` | Return type is `ContextResult`, not `str` |
| `test_load_full_context_failed_carries_error` | `OSError` → `status=FAILED` with error message in `.error` |
| `test_load_search_context_returns_context_result` | Return type is `ContextResult` |
| `test_load_synthesis_context_returns_context_result` | Return type is `ContextResult` |

### Risk flags

- **HIGH RISK: 18+ test updates across 3 files.** This is the highest-breakage session. All changes are mechanical (swap `str` assertions to `ContextResult` assertions) but there are many of them. Run the full test suite after EACH file update, not just at the end.
- The `tests/test_decompose.py` tests for `load_full_context` are in an unexpected location (legacy placement). Don't miss them.

---

## Deliverable 2: Token Budget Enforcement

**Files modified:** `research_agent/token_budget.py` (add helper), `research_agent/synthesize.py`
**Tests modified:** None expected to break
**New test file:** `tests/test_synthesize_budget.py` (or append to `tests/test_synthesize.py`)
**Estimated lines:** ~50 delta (production), ~40 (new tests)

### What changes

**`token_budget.py` — add `truncate_to_budget()` helper (~10 lines):**

```python
def truncate_to_budget(text: str, max_tokens: int) -> str:
    """Truncate text to fit within a token budget.

    Uses the conservative 4-chars-per-token estimate for truncation
    (avoids an API call per truncation). Appends "[truncated]" marker
    when content is cut.

    Args:
        text: Content to potentially truncate.
        max_tokens: Maximum allowed tokens.

    Returns:
        Original text if within budget, truncated text otherwise.
    """
    if not text:
        return text
    current = count_tokens(text)
    if current <= max_tokens:
        return text
    # Truncate by character estimate (conservative: 4 chars/token)
    max_chars = max_tokens * 4
    return text[:max_chars] + "\n\n[Content truncated to fit token budget]"
```

**`synthesize.py` — add budget checks to `synthesize_report()` and `synthesize_final()`:**

#### `synthesize_report()` — insert after `sources_text = _build_sources_context(summaries)` (line 68)

```python
# Token budget enforcement
from .token_budget import allocate_budget, truncate_to_budget

components = {"sources": sources_text, "instructions": mode_instructions}
if business_context:
    components["business_context"] = sanitize_content(business_context)

budget = allocate_budget(
    components,
    max_tokens=100_000,  # Model context limit
    reserved_output=max_tokens,  # Reserve space for model output
)
if budget.pruned:
    logger.info(f"Token budget: pruned {budget.pruned}")
    for name in budget.pruned:
        if name == "sources":
            sources_text = truncate_to_budget(sources_text, budget.allocations.get("sources", 0))
        elif name == "business_context" and business_context:
            business_context = truncate_to_budget(
                business_context, budget.allocations.get("business_context", 0)
            )
```

#### `synthesize_final()` — insert after `sources_text = _build_sources_context(summaries)` (line 348)

Same pattern but with additional components: `draft_analysis`, `skeptic_findings`, `business_context`, `sources`.

```python
components = {
    "sources": sources_text,
    "instructions": section_list,  # Never pruned (priority 6)
}
if business_context:
    components["business_context"] = sanitize_content(business_context)
if safe_draft:
    components["previous_baseline"] = safe_draft
if skeptic_block:
    components["staleness_metadata"] = skeptic_block  # Lowest priority

budget = allocate_budget(components, max_tokens=100_000, reserved_output=max_tokens)
if budget.pruned:
    logger.info(f"Token budget: pruned {budget.pruned}")
    # Apply truncation to pruned components
    for name in budget.pruned:
        if name == "sources":
            sources_text = truncate_to_budget(sources_text, budget.allocations.get("sources", 0))
        elif name == "business_context" and business_context:
            business_context = truncate_to_budget(
                business_context, budget.allocations.get("business_context", 0)
            )
```

**New imports in `synthesize.py`:**
```python
from .token_budget import allocate_budget, truncate_to_budget
```

### Acceptance criteria

1. `truncate_to_budget()` returns original text when within budget
2. `truncate_to_budget()` appends `[truncated]` marker when content is cut
3. `synthesize_report()` calls `allocate_budget()` before building the prompt
4. `synthesize_final()` calls `allocate_budget()` before building the prompt
5. Instructions component (priority 6) is never pruned
6. When all components fit, no truncation occurs (zero behavioral change for typical queries)
7. Logs when truncation happens (for debugging token budget issues)

### Tests that WILL break

**None.** The budget enforcement is additive — it only activates when components exceed the budget, which doesn't happen in existing tests (mock summaries are small). Existing tests pass small inputs that fit well within 100K token budget.

### New tests

| Test | Validates |
|------|-----------|
| `test_truncate_to_budget_passthrough` | Text within budget returned unchanged |
| `test_truncate_to_budget_truncates` | Oversized text truncated with `[truncated]` marker |
| `test_truncate_to_budget_empty` | Empty string returned as-is |
| `test_synthesize_report_calls_budget` | Mock `allocate_budget` called during `synthesize_report()` |
| `test_synthesize_final_calls_budget` | Mock `allocate_budget` called during `synthesize_final()` |
| `test_budget_prunes_context_before_sources` | When over budget, `business_context` pruned before `sources` |

### Risk flags

- **LOW RISK.** Budget enforcement is additive — it gates prompt construction but doesn't change the prompt format. Existing tests use small inputs that never trigger pruning.
- The `100_000` token limit is hardcoded. In Session 4, this will be replaced by `CycleConfig.max_tokens_per_prompt`. For now, hardcode is fine.

---

## Deliverable 3: Relevance Gate Extension

**File modified:** `research_agent/relevance.py`
**Tests modified:** None expected to break
**Estimated lines:** ~30 delta (production), ~30 (new tests)

### What changes

#### `evaluate_sources()` — add `no_new_findings` decision (lines 320-340)

Current decision logic:
```python
if total_survived >= mode.min_sources_full_report:
    decision = "full_report"
elif total_survived >= mode.min_sources_short_report:
    decision = "short_report"
else:
    decision = "insufficient_data"
```

New decision logic:
```python
if total_survived >= mode.min_sources_full_report:
    decision = "full_report"
elif total_survived >= mode.min_sources_short_report:
    decision = "short_report"
elif total_scored > 0 and total_survived == 0:
    decision = "no_new_findings"
    rationale = (
        f"All {total_scored} sources scored below {mode.relevance_cutoff}, "
        f"suggesting no new relevant information is publicly available"
    )
else:
    decision = "insufficient_data"
```

The distinction: `no_new_findings` means "we searched, found sources, scored them all, but none were relevant." `insufficient_data` means "no sources found at all" (empty summaries). This distinction matters for Session 5 — `no_new_findings` triggers `mark_checked()` (we looked), while `insufficient_data` from empty search triggers no state update.

#### `_evaluate_and_synthesize()` in agent.py — handle new decision (Session 4/5 will complete this)

For now, `no_new_findings` falls through to the same handler as `insufficient_data`:

```python
if evaluation.decision in ("insufficient_data", "no_new_findings"):
    self._next_step("Generating insufficient data response...")
    return await generate_insufficient_data_response(...)
```

The behavioral difference (state updates) is added in Session 5.

### Acceptance criteria

1. `no_new_findings` decision is emitted when `total_scored > 0` and `total_survived == 0`
2. `insufficient_data` is still emitted when `total_scored == 0` (no sources at all)
3. The existing three decisions (`full_report`, `short_report`, `insufficient_data`) are unchanged
4. `no_new_findings` response uses the same `generate_insufficient_data_response()` handler (for now)

### Tests that WILL break

**None.** The new decision only fires when `total_scored > 0 and total_survived == 0`, which is a subset of the old `insufficient_data` case. Existing tests that trigger `insufficient_data` with `total_scored == 0` (no summaries) are unchanged.

### New tests

| Test | Validates |
|------|-----------|
| `test_evaluate_no_new_findings` | Sources scored but all below cutoff → `no_new_findings` |
| `test_evaluate_insufficient_data_no_sources` | No summaries at all → `insufficient_data` (unchanged) |
| `test_no_new_findings_vs_insufficient_data` | Verifies these are distinct decisions for the same "no results" scenario |

### Risk flags

- **LOW RISK.** The new decision is carved out of a subset of `insufficient_data`. No existing code paths change.
- The `no_new_findings` decision temporarily shares the `insufficient_data` handler. Session 5 adds the state-update behavior.

---

## Deliverable 4: Pre-Research Gap Check

**File modified:** `research_agent/agent.py`
**Tests modified:** None expected to break
**Estimated lines:** ~45 delta (production), ~50 (new tests)

### What changes

#### `ResearchAgent.__init__()` — accept `CycleConfig` and `schema_path`

```python
def __init__(
    self,
    api_key: str | None = None,
    max_sources: int | None = None,
    mode: ResearchMode | None = None,
    cycle_config: CycleConfig | None = None,
    schema_path: Path | str | None = None,
):
    ...
    self.cycle_config = cycle_config or CycleConfig()
    self.schema_path = Path(schema_path) if schema_path else None
```

#### `_research_async()` — add gap check before search (insert after decomposition, before line 119)

```python
# Pre-research gap check (if schema configured)
schema_result = None
research_batch = None
if self.schema_path:
    from .schema import load_schema, sort_gaps
    from .staleness import detect_stale, select_batch

    schema_result = load_schema(self.schema_path)
    if schema_result:
        # Detect stale gaps
        stale = detect_stale(
            schema_result.gaps,
            default_ttl_days=self.cycle_config.default_ttl_days,
        )
        # Combine stale + unknown gaps as research candidates
        stale_ids = {g.id for g in stale}
        candidates = tuple(
            g for g in schema_result.gaps
            if g.id in stale_ids or g.status == GapStatus.UNKNOWN
        )
        if not candidates:
            # All gaps verified and fresh — return early
            return self._already_covered_response(schema_result)
        research_batch = select_batch(candidates, self.cycle_config.max_gaps_per_run)
        print(f"      Gap schema: {len(research_batch)} gaps to research "
              f"({len(stale)} stale, {sum(1 for g in candidates if g.status == GapStatus.UNKNOWN)} unknown)")
```

#### New `_already_covered_response()` method

```python
def _already_covered_response(self, schema_result: SchemaResult) -> str:
    """Generate a response when all gaps are verified and fresh."""
    gap_count = len(schema_result.gaps)
    return (
        f"# All Intelligence Current\n\n"
        f"All {gap_count} gaps in the schema are verified and within their "
        f"freshness windows. No new research needed at this time.\n\n"
        f"Run with `--force` to research anyway, or wait for gaps to become stale."
    )
```

#### Store `research_batch` and `schema_result` on instance for Session 5

```python
self._current_schema_result = schema_result
self._current_research_batch = research_batch
```

**New imports in `agent.py`:**
```python
from pathlib import Path
from .cycle_config import CycleConfig
from .schema import GapStatus, SchemaResult
```

### Acceptance criteria

1. When `schema_path` is `None`, pipeline behaves exactly as before (backward compatibility)
2. When schema exists and all gaps are verified + fresh, returns early with `already_covered` message
3. When schema exists and some gaps are stale/unknown, pipeline continues normally
4. `select_batch()` limits how many gaps are researched per run (uses `CycleConfig.max_gaps_per_run`)
5. Stale detection uses `CycleConfig.default_ttl_days` as fallback
6. Console output shows gap status summary
7. `ResearchAgent` accepts `cycle_config` and `schema_path` as optional constructor parameters

### Tests that WILL break

**None.** The new constructor parameters are optional with defaults. Existing tests don't pass `cycle_config` or `schema_path`, so the gap check is skipped entirely (`if self.schema_path:` is `False`).

### New tests

| Test | Validates |
|------|-----------|
| `test_init_default_cycle_config` | `ResearchAgent()` uses `CycleConfig()` defaults |
| `test_init_custom_cycle_config` | Custom `CycleConfig` is stored on instance |
| `test_pre_research_no_schema_unchanged` | With no `schema_path`, pipeline runs normally (backward compat) |
| `test_pre_research_all_verified_returns_early` | All gaps verified+fresh → `already_covered` response returned without search |
| `test_pre_research_stale_gaps_continues` | Some stale gaps → pipeline continues with batch selection |
| `test_pre_research_unknown_gaps_continues` | Unknown gaps → pipeline continues |
| `test_pre_research_batch_limit_respected` | With 10 stale gaps and `max_gaps_per_run=3`, only 3 selected |
| `test_pre_research_empty_schema_proceeds` | Empty schema (no gaps) → pipeline runs normally |

### Risk flags

- **MEDIUM RISK.** This adds early-return logic to `_research_async()`, the main pipeline entry point. If the gap check incorrectly triggers, it could skip research when it shouldn't.
- **Mitigation:** The check only fires when `self.schema_path` is set AND schema has gaps AND all are verified+fresh. Three conditions must be true for early return.
- Importing `schema` and `staleness` modules inside the method (lazy import) avoids circular import risk and keeps startup fast when no schema is configured.

---

## Deliverable 5: Post-Research State Update

**File modified:** `research_agent/agent.py`
**Tests modified:** None expected to break
**Estimated lines:** ~35 delta (production), ~40 (new tests)

### What changes

#### `_evaluate_and_synthesize()` — add state updates after synthesis

Insert at the end of the method (before return statements) a state update hook:

```python
# Post-research state update (if schema configured)
if self.schema_path and self._current_research_batch:
    self._update_gap_states(evaluation.decision)
```

#### New `_update_gap_states()` method

```python
def _update_gap_states(self, decision: str) -> None:
    """Update gap schema after research completes.

    - full_report / short_report → mark_verified() for researched gaps
    - no_new_findings → mark_checked() (searched but found nothing)
    - insufficient_data → no state update (search itself failed)
    """
    from .state import mark_verified, mark_checked, save_schema
    from .staleness import log_flip
    from .schema import load_schema, GapStatus

    schema_result = load_schema(self.schema_path)
    if not schema_result:
        return

    batch_ids = {g.id for g in self._current_research_batch}
    updated_gaps: list[Gap] = []
    audit_log_path = self.schema_path.parent / "gap_audit.log"

    for gap in schema_result.gaps:
        if gap.id not in batch_ids:
            updated_gaps.append(gap)
            continue

        if decision in ("full_report", "short_report"):
            new_gap = mark_verified(gap)
            if gap.status != new_gap.status:
                log_flip(
                    audit_log_path, gap.id,
                    gap.status, new_gap.status,
                    reason=f"Research completed: {decision}",
                )
            updated_gaps.append(new_gap)
        elif decision == "no_new_findings":
            new_gap = mark_checked(gap)
            updated_gaps.append(new_gap)
            logger.info(f"Gap '{gap.id}' checked (no new findings)")
        else:
            # insufficient_data — don't update state
            updated_gaps.append(gap)

    try:
        save_schema(self.schema_path, tuple(updated_gaps))
        logger.info(f"Updated {len(batch_ids)} gap states in {self.schema_path}")
    except StateError as e:
        logger.warning(f"Failed to save gap state: {e}")
```

#### Wire into `_evaluate_and_synthesize()` return paths

The method has multiple return points:
1. `insufficient_data` early return (line 288) — NO state update
2. Quick mode `synthesize_report()` return (line 311-320) — state update with decision
3. Standard/deep mode `synthesize_final()` return (line 361-371) — state update with decision

Add the state update call before each return:

```python
# Before return in quick mode (after synthesize_report):
report = synthesize_report(...)
if self.schema_path and self._current_research_batch:
    self._update_gap_states("full_report" if not limited_sources else "short_report")
return report

# Before return in standard/deep mode (after synthesize_final):
result = await asyncio.to_thread(synthesize_final, ...)
if self.schema_path and self._current_research_batch:
    self._update_gap_states("full_report" if not limited_sources else "short_report")
return result
```

For `no_new_findings` (handled in Session 3's decision branch):
```python
if evaluation.decision in ("insufficient_data", "no_new_findings"):
    if evaluation.decision == "no_new_findings" and self.schema_path and self._current_research_batch:
        self._update_gap_states("no_new_findings")
    return await generate_insufficient_data_response(...)
```

### Acceptance criteria

1. After `full_report` or `short_report`, researched gaps are `mark_verified()` (status=VERIFIED, timestamps updated)
2. After `no_new_findings`, researched gaps are `mark_checked()` (last_checked updated, status unchanged)
3. After `insufficient_data`, no state changes (search itself failed — can't confirm we checked)
4. Audit log records every status flip with timestamp and reason
5. State save failure is logged but does NOT crash the pipeline (graceful degradation)
6. When `schema_path` is `None`, no state updates occur (backward compatibility)
7. Only gaps in the current batch are updated — other gaps are unchanged

### Tests that WILL break

**None.** State updates only trigger when `schema_path` is set AND `_current_research_batch` is populated. Existing tests don't set either.

### New tests

| Test | Validates |
|------|-----------|
| `test_post_research_marks_verified_on_full_report` | After `full_report`, batch gaps have `status=VERIFIED` |
| `test_post_research_marks_verified_on_short_report` | After `short_report`, batch gaps have `status=VERIFIED` |
| `test_post_research_marks_checked_on_no_findings` | After `no_new_findings`, batch gaps have updated `last_checked` but status unchanged |
| `test_post_research_no_update_on_insufficient` | After `insufficient_data`, gap states unchanged |
| `test_post_research_no_schema_no_update` | Without `schema_path`, no state writes |
| `test_post_research_preserves_other_gaps` | Non-batch gaps unchanged in schema file |
| `test_post_research_audit_log_written` | Status flips recorded in `gap_audit.log` |
| `test_post_research_save_failure_logged` | `StateError` logged but pipeline returns successfully |

### Risk flags

- **MEDIUM RISK.** Multiple return paths in `_evaluate_and_synthesize()` each need the state update call. Missing one means that code path silently skips state updates.
- **Mitigation:** The plan explicitly lists all three return paths (insufficient_data, quick mode, standard/deep mode) and where the hook goes.
- `StateError` from `save_schema()` is caught and logged, not re-raised. A failed state save should never crash the pipeline or lose the research report.

---

## Summary Table

| # | Deliverable | Files (production) | Files (tests) | Est. Lines (prod) | Est. Lines (tests) | Existing tests broken |
|---|-------------|-------------------|---------------|-------------------|--------------------|----------------------|
| 1 | Context loader refactor | `context.py`, `agent.py` | `test_context.py`, `test_decompose.py`, `test_agent.py` | ~30 | ~40 | **~18 tests updated** |
| 2 | Token budget enforcement | `token_budget.py`, `synthesize.py` | `test_synthesize_budget.py` (new section) | ~50 | ~40 | 0 |
| 3 | Relevance gate extension | `relevance.py` | `test_relevance.py` | ~30 | ~30 | 0 |
| 4 | Pre-research gap check | `agent.py` | `test_agent.py` | ~45 | ~50 | 0 |
| 5 | Post-research state update | `agent.py` | `test_agent.py` | ~35 | ~40 | 0 |
| | **Totals** | **5 production files** | **4 test files** | **~190** | **~200** | **~18** |

---

## What This Cycle Does NOT Touch

- **No new files** — all changes modify existing modules
- **No changes to `decompose.py`** — `load_search_context` is loaded but not yet wired into decomposition (Seam D deferred to a future cycle where `decompose.py` gains a `business_context` parameter)
- **No changes to `skeptic.py`** — skeptic receives `synthesis_context` as `str | None` from agent.py, unchanged
- **No changes to `schema.py`** — 17B's module is read-only; agent.py calls its API
- **No changes to `state.py`** or `staleness.py` — 17C's modules are consumed, not modified
- **No Google Drive** — deferred to Cycle 22
- **No delta output** — deferred to Cycle 23
- **No `--force` flag implementation** — the `already_covered` message mentions it but the flag itself is Cycle 18+

---

## What This Cycle Unlocks

| Downstream Cycle | What it enables |
|-----------------|-----------------|
| **18** (Pip Package) | Clean public API with `ResearchAgent(schema_path=..., cycle_config=...)` |
| **22** (Google Drive) | Swap file reader in `context.py` → `ContextResult` API is ready |
| **23** (Delta Output) | State is persistent → before/after comparison becomes possible |
| **All future cycles** | Token budgets prevent context overflow regardless of what new components are added |

---

## Risk Mitigations Addressed

| Risk ID | Risk | How 17D addresses it |
|---------|------|---------------------|
| F5.2 | Context window budget war (#1 risk) | `allocate_budget()` enforced in both synthesis functions |
| F5.1 | Error cascade across features (#3 risk) | `ContextResult` distinguishes failed from missing — no silent degradation |
| F1.1 | Context overflow from Drive docs (#4 risk) | Token budget truncates any oversized component before it reaches the API |
| Edge Case 2 | Fully populated schema | `already_covered` early return skips unnecessary research |
| Edge Case 3 | 20 gaps stale at once | `select_batch()` caps per-run gap count |
| Edge Case 7 | Research finds nothing | `no_new_findings` vs `insufficient_data` distinction |
| F4.5 | No audit trail | `log_flip()` records every status change |
| F4.6 | Infinite re-research loop | `mark_checked()` vs `mark_verified()` distinction prevents re-research of gaps where nothing was found |

---

## Implementation Sessions

Each session = one commit of ~30-50 lines production code.

| Session | Commit message | Files touched |
|---------|---------------|---------------|
| 1 | `feat(17D-1): refactor context loaders to return ContextResult` | `research_agent/context.py`, `research_agent/agent.py`, `tests/test_context.py`, `tests/test_decompose.py`, `tests/test_agent.py` |
| 2 | `feat(17D-2): add token budget enforcement to synthesis` | `research_agent/token_budget.py`, `research_agent/synthesize.py`, `tests/test_synthesize.py` (or new section) |
| 3 | `feat(17D-3): extend relevance gate with no_new_findings decision` | `research_agent/relevance.py`, `tests/test_relevance.py` |
| 4 | `feat(17D-4): add pre-research gap check with schema awareness` | `research_agent/agent.py`, `tests/test_agent.py` |
| 5 | `feat(17D-5): add post-research state updates with audit logging` | `research_agent/agent.py`, `tests/test_agent.py` |

**Critical:** Run full test suite (`python3 -m pytest tests/ -v`) after EVERY session. Session 1 is the highest-risk commit (18 test updates). If tests fail after Session 1, fix them before proceeding.

After all 5 sessions: verify all 542 existing tests + ~30 new tests pass.

---

## Backward Compatibility Guarantee

The pipeline must produce identical output for any user who does NOT configure a gap schema. This is enforced by:

1. `CycleConfig()` has sensible defaults — no config needed
2. `schema_path=None` (default) skips all gap-related logic
3. Token budget enforcement only truncates when over 100K tokens — normal queries never hit this
4. `no_new_findings` is carved out of `insufficient_data` — the handler is the same (for now)
5. Context loaders return `ContextResult` but agent.py extracts `.content` → downstream functions see `str | None` as before
