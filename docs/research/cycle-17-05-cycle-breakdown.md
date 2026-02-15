# Cycle 17-05: Sequential Cycle Breakdown

**Date:** 2026-02-12
**Type:** Research (no code, no planning)
**Inputs:** Codebase analysis (17-01), best practices (17-02), failure modes (17-03), edge cases (17-04)
**Purpose:** Break the full Cycle 17 scope into 3-5 sequential cycles, each completable in one Claude Code session

---

## Ordering Rationale

Three principles govern the sequence:

1. **Foundation before features.** The research identified three infrastructure gaps that every feature depends on: exception hierarchy (F5.3), token budgeting (F5.2), and the three-way state distinction (Edge Cases cross-cutting pattern). These must exist before any feature code touches agent.py.

2. **Highest risk earliest.** The failure mode analysis ranks context window budget war (F5.2) as the #1 risk. Exception hierarchy gaps (F5.3) are ranked #8 by severity but are a prerequisite for everything — they're #1 in build order. Schema parse crashes (F2.1) and cascading status flips (F4.1) come next because they're CRITICAL failures in the next layer up.

3. **Each cycle produces a standalone, testable module.** No cycle ends with a half-wired module. Each cycle's output works independently (with its own tests) and exposes a clean API for the next cycle to consume. Integration into agent.py happens last, once all the pieces exist.

---

## Cycle 17A: Foundation Infrastructure

**Theme:** Build the utilities that every subsequent cycle depends on. Zero feature code — only error types, token math, safe I/O, and the three-way state pattern.

### What it builds

| Component | File(s) | Lines (est.) | Purpose |
|-----------|---------|-------------|---------|
| Exception hierarchy expansion | `errors.py` | ~30 | `ContextError` (+ `ContextNotConfiguredError`, `ContextLoadError`, `ContextAuthError`), `SchemaError`, `StateError` |
| Context result type | `context_result.py` (new) | ~50 | Dataclass replacing `str | None` with `(content, status, source)` where status is `loaded / not_configured / empty / failed` |
| Token budget utilities | `token_budget.py` (new) | ~80 | `count_tokens(text)` using `anthropic.count_tokens` or tiktoken fallback. `allocate_budget(components, max_tokens)` returns a dict of component→allowed_tokens with priority-based pruning |
| Atomic file writer | `safe_io.py` (new) | ~30 | `atomic_write(path, content)` — write-to-tempfile + `os.rename`. Prevents the state corruption failures F3.3 and F4.4 |

### Why this order

- **Exception types first** because every subsequent module needs to raise specific errors. Without `SchemaError`, Cycle 17B would have to raise `ValueError` and retrofit later.
- **Context result type second** because the three-way distinction (not-configured vs. empty vs. failed) is the cross-cutting pattern that Edge Cases 1, 2, 4, and 7 all require. Building it here means Cycle 17D can wire it in without redesigning context.py's API.
- **Token budget third** because it's the #1 risk (F5.2) and the hardest to bolt on later. Every synthesis prompt will eventually call `allocate_budget()`. Building it now means Cycle 17D integration is straightforward.
- **Atomic writes last** because it's simple, self-contained, and needed by Cycle 17C's state persistence.

### What it depends on

Nothing. This cycle has zero external dependencies. All four components are pure Python utilities with no network I/O, no API calls, no file system side effects (except atomic write, which is tested with tempfiles).

### Tests that prove it works

| Test | What it validates |
|------|-------------------|
| `test_context_error_hierarchy` | All new exceptions subclass `ResearchError`. `ContextLoadError` and `ContextAuthError` subclass `ContextError`. |
| `test_context_result_states` | Result type correctly carries content for `loaded`, None for `not_configured`, None for `empty`, error details for `failed` |
| `test_context_result_is_truthy_only_when_loaded` | Boolean coercion: `bool(result)` is True only for `loaded` status |
| `test_count_tokens_returns_int` | Token counter returns a positive integer for non-empty strings, 0 for empty |
| `test_allocate_budget_within_limit` | Allocated tokens sum to at most `max_tokens` |
| `test_allocate_budget_prunes_by_priority` | When over budget, lowest-priority components are pruned first (staleness metadata → baseline → schema → context) |
| `test_allocate_budget_preserves_minimum` | Each component gets at least a minimum allocation (prevents zero-token starvation) |
| `test_atomic_write_succeeds` | File contains expected content after write |
| `test_atomic_write_no_partial_on_crash` | If write raises mid-content, original file is unchanged (simulated via mock) |
| `test_atomic_write_creates_parent_dirs` | Creates intermediate directories if needed |

**Estimated commits:** 4 (one per component)
**Estimated total lines:** ~190

### What it unlocks

- Cycle 17B can raise `SchemaError` with structured details instead of generic exceptions
- Cycle 17C can use `atomic_write()` for state persistence and `StateError` for failures
- Cycle 17D can use `ContextResult` in context.py and `allocate_budget()` in synthesize.py
- The degradation hierarchy from F5.5 is encoded in `allocate_budget()`'s priority order

---

## Cycle 17B: Gap Schema Layer

**Theme:** Parse, validate, and prioritize structured gap schemas. A standalone module that works independently from the research pipeline — it reads a YAML file and returns a prioritized list of gaps.

### What it builds

| Component | File(s) | Lines (est.) | Purpose |
|-----------|---------|-------------|---------|
| Gap data model | `schema.py` (new) | ~70 | Frozen dataclass `Gap` with fields: `id, category, status, priority, last_verified, last_checked, ttl_days, blocks, blocked_by, findings, metadata`. Status enum: `unknown / verified / stale / blocked` |
| Schema parser | `schema.py` | ~50 | `load_schema(path) -> SchemaResult` — reads YAML file, returns list of `Gap` objects or `SchemaError`. Uses Cycle 17A's three-way result pattern: not-configured / empty / failed |
| Schema validator | `schema.py` | ~80 | Consistency checks: status/timestamp coherence (verified requires last_verified), reference integrity (all blocked_by IDs exist), self-reference detection, type checking. Reports ALL errors, not just first |
| Cycle detector | `schema.py` | ~40 | DFS-based cycle detection on the `blocks`/`blocked_by` DAG. Returns the specific nodes forming each cycle (not just "cycle exists") |
| Priority sorter | `schema.py` | ~50 | Topological sort (Kahn's algorithm) with priority-based tiebreaking. Cycled nodes reported as warnings, sorted by priority as fallback |

### Why this order within the cycle

- **Data model first** because parser, validator, and sorter all operate on `Gap` objects.
- **Parser second** because validation and sorting need parsed input.
- **Validator third** because sorting assumes valid data (no cycles, consistent statuses).
- **Cycle detector and priority sorter last** because they build on validated data.

### What it depends on

- **Cycle 17A:** `SchemaError` for parse/validation failures. The three-way result pattern for `load_schema()` return type.

### Tests that prove it works

| Test | What it validates | Addresses |
|------|-------------------|-----------|
| `test_parse_valid_schema` | Correctly parses a well-formed YAML schema into `Gap` objects | Basic functionality |
| `test_parse_empty_schema` | Empty file returns `SchemaResult` with status `empty`, not an error | Edge Case 1 |
| `test_parse_missing_file` | Missing file returns status `not_configured` | Three-way distinction |
| `test_parse_malformed_yaml` | Broken YAML raises `SchemaError` with line number and description | F2.1 |
| `test_validate_verified_needs_timestamp` | `status: verified` with `last_verified: null` fails validation | Edge Case 6 |
| `test_validate_unknown_has_no_timestamp` | `status: unknown` with non-null `last_verified` fails validation | Edge Case 6 |
| `test_validate_references_exist` | `blocked_by: ["nonexistent"]` fails with "gap 'nonexistent' not found" | Edge Case 6 |
| `test_validate_reports_all_errors` | Schema with 3 errors reports all 3, not just the first | Usability |
| `test_detect_simple_cycle` | A→B→A detected and both nodes reported | F2.2 |
| `test_detect_deep_cycle` | A→B→C→A detected | F2.2 |
| `test_no_false_cycle` | Linear chain A→B→C→D has no cycle | Correctness |
| `test_sort_respects_dependencies` | If A blocks B, A appears before B | Topological sort |
| `test_sort_breaks_ties_by_priority` | Among unblocked gaps, higher priority comes first | Prioritization |
| `test_sort_handles_all_unknown` | When all gaps are `unknown`, falls back to priority-only ordering | Edge Case 1 |
| `test_sort_warns_on_cycled_nodes` | Cycled nodes appear in output (sorted by priority) with warning flag | F2.2 mitigation |
| `test_fully_populated_schema` | All gaps `verified` and fresh — sorter returns empty "needs work" list | Edge Case 2 |

**Estimated commits:** 4-5 (data model, parser, validator, cycle detector, priority sorter)
**Estimated total lines:** ~290

### What it unlocks

- Cycle 17C can add timestamps and staleness detection on top of the `Gap` data model
- Cycle 17D can call `load_schema()` in the pre-research check and use the prioritized gap list to generate queries
- The validator catches the CRITICAL failures F2.1 (malformed schema) and F2.2 (circular deps) before any research runs

---

## Cycle 17C: State Persistence + Staleness Detection

**Theme:** Write gap state back to disk after research runs. Detect and manage staleness with per-gap TTLs. This cycle makes the schema layer from 17B persistent and temporal.

### What it builds

| Component | File(s) | Lines (est.) | Purpose |
|-----------|---------|-------------|---------|
| State writer | `state.py` (new) | ~60 | `save_schema(path, gaps)` — serializes `Gap` objects back to YAML via `atomic_write()`. `update_gap(path, gap_id, changes)` — loads, validates, updates one gap, saves. Both use atomic writes from Cycle 17A |
| Timestamp management | `state.py` | ~40 | `mark_checked(gap)` — sets `last_checked` to now (searched but maybe found nothing). `mark_verified(gap)` — sets `last_verified` to now and `status: verified` (found something). Distinction prevents re-research loops (F4.6) |
| Staleness detector | `staleness.py` (new) | ~70 | `detect_stale(gaps) -> list[Gap]` — compares each gap's `last_verified` against its `ttl_days`. Only flips the gap's own status — does NOT cascade through dependencies (prevents F4.1). Returns list of newly-stale gaps |
| Batch limiter | `staleness.py` | ~30 | `select_batch(stale_gaps, max_per_run) -> list[Gap]` — selects top N stale gaps by priority score. Prevents the "20 gaps stale at once" overload (Edge Case 3) |
| Audit logger | `staleness.py` | ~40 | `log_flip(gap, old_status, new_status, reason)` — appends to an audit log file. Structured format: timestamp, gap_id, old→new, reason. Addresses the "no undo / audit trail" gap (F4.5) |

### Why this order within the cycle

- **State writer first** because staleness detection needs to read and write state.
- **Timestamps second** because staleness detection compares timestamps.
- **Staleness detector third** because it's the core feature, building on writer + timestamps.
- **Batch limiter fourth** because it post-processes staleness results.
- **Audit logger last** because it's an output of staleness detection, not an input.

### What it depends on

- **Cycle 17A:** `atomic_write()` for safe file writes. `StateError` for write failures.
- **Cycle 17B:** `Gap` data model, `load_schema()`, `validate_schema()`. The state writer serializes `Gap` objects. The staleness detector operates on validated `Gap` lists.

### Tests that prove it works

| Test | What it validates | Addresses |
|------|-------------------|-----------|
| `test_save_load_roundtrip` | Save gaps to YAML, load them back, get identical objects | Basic persistence |
| `test_save_uses_atomic_write` | Save goes through `atomic_write`, not direct `Path.write_text` | F4.4 |
| `test_update_single_gap` | Updating one gap doesn't affect others | Isolation |
| `test_mark_checked_sets_timestamp` | `mark_checked` updates `last_checked` but NOT `last_verified` or `status` | Edge Case 7 |
| `test_mark_verified_sets_both` | `mark_verified` updates `last_verified`, `last_checked`, and `status` | Correctness |
| `test_detect_stale_by_ttl` | Gap with `last_verified` older than `ttl_days` detected as stale | F4.2 |
| `test_detect_stale_ignores_unknown` | Gaps with `status: unknown` are not flipped to stale (they were never verified) | Edge Case 1 |
| `test_no_cascade_through_dependencies` | If A blocks B and A goes stale, B's status is unchanged | F4.1 |
| `test_batch_selects_highest_priority` | With 10 stale gaps and max_per_run=3, top 3 by priority are selected | Edge Case 3 |
| `test_batch_respects_limit` | Never returns more than `max_per_run` gaps | Safety valve |
| `test_audit_log_records_flip` | Flip event written to audit log with timestamp, gap_id, old/new status, reason | F4.5 |
| `test_audit_log_is_append_only` | Multiple flips append to same file, don't overwrite | Audit integrity |
| `test_stale_with_no_ttl_uses_default` | Gap without `ttl_days` uses a sensible default (e.g., 30 days) | Usability |

**Estimated commits:** 4-5 (state writer, timestamps, staleness detector, batch limiter, audit logger)
**Estimated total lines:** ~240

### What it unlocks

- Cycle 17D can wire staleness detection into the pre-research check — the agent knows what's stale before searching
- The state writer enables the pipeline to close the loop: research → update gaps → persist
- The audit log makes staleness behavior debuggable (Edge Case 3, 6, 7)
- Future delta output can compare current state vs. previous state because state is now persistent

---

## Cycle 17D: Pipeline Integration

**Theme:** Wire all foundation modules into the existing research pipeline. This is the cycle where agent.py, context.py, and synthesize.py learn about schemas, budgets, and state. No new standalone modules — only integration code and the new relevance gate decisions.

### What it builds

| Component | File(s) | Lines (est.) | Purpose |
|-----------|---------|-------------|---------|
| Context loader refactor | `context.py` | ~40 (delta) | Replace `str | None` returns with `ContextResult` from Cycle 17A. All three loaders (`load_full_context`, `load_synthesis_context`, `load_search_context`) return result objects. Callers branch on `.status`, not null-checking |
| Token budget enforcement | `synthesize.py` | ~50 (delta) | Before building any synthesis prompt, call `allocate_budget()` with all components (context, sources, schema, instructions). Truncate components that exceed their allocation. Log when truncation happens |
| Relevance gate extension | `relevance.py` | ~30 (delta) | Add two new decisions: `already_covered` (all relevant gaps are verified and fresh) and `no_new_findings` (searched successfully, found nothing relevant). Extends the existing three-way branch to five-way |
| Pre-research gap check | `agent.py` | ~40 (delta) | Before entering the search pipeline, load the gap schema (if configured). If all relevant gaps are verified and fresh, return early with `already_covered` decision. If some gaps are stale, use them to inform query generation. Wire `load_search_context()` (currently dead code, Seam D from 17-01) |
| Post-research state update | `agent.py` | ~30 (delta) | After successful synthesis, update researched gaps: `mark_verified()` for gaps with findings, `mark_checked()` for gaps that were searched but had no results. Uses the state writer from Cycle 17C |

### Why this order within the cycle

- **Context loader refactor first** because it changes the API that everything else in this cycle calls. All subsequent integration code uses `ContextResult`, not raw strings.
- **Token budget enforcement second** because it changes how synthesis prompts are built. Must be in place before new context sources (schema data) are added to prompts.
- **Relevance gate third** because it adds the decision branches that the pre-research check triggers.
- **Pre-research gap check fourth** because it calls the relevance gate and context loader.
- **Post-research state update last** because it runs after the pipeline completes — it depends on knowing what was researched and what was found.

### What it depends on

- **Cycle 17A:** `ContextResult` for context loader refactor. `allocate_budget()` for token enforcement. Exception types for error handling throughout.
- **Cycle 17B:** `load_schema()` and `Gap` model for pre-research check. Priority-sorted gap list for query generation.
- **Cycle 17C:** `mark_verified()`, `mark_checked()`, `save_schema()` for post-research state update. `detect_stale()` for pre-research check.

### Tests that prove it works

| Test | What it validates | Addresses |
|------|-------------------|-----------|
| `test_context_loader_returns_result_type` | All three loaders return `ContextResult`, not `str | None` | Three-way distinction |
| `test_context_missing_file_is_not_configured` | Missing file → `ContextResult(status=not_configured)`, not `None` | Edge Case 4 |
| `test_context_empty_file_is_empty` | Empty file → `ContextResult(status=empty)` | Edge Case 1 |
| `test_synthesis_prompt_within_budget` | Built prompt token count does not exceed model's context limit | F5.2 |
| `test_budget_truncates_lowest_priority` | When context + sources exceed budget, context is truncated before sources are | Degradation hierarchy |
| `test_relevance_gate_already_covered` | All gaps verified + fresh → `already_covered` decision | Edge Case 2 |
| `test_relevance_gate_no_new_findings` | Successful search with zero relevant results → `no_new_findings` | Edge Case 7 |
| `test_pre_research_skips_if_covered` | With all-verified schema, pipeline returns early without searching | Edge Case 2 |
| `test_pre_research_proceeds_if_stale` | With stale gaps, pipeline runs normally and targets stale gaps | Edge Case 3 |
| `test_post_research_marks_verified` | After successful synthesis, researched gaps have `status: verified` and fresh timestamps | State loop closure |
| `test_post_research_marks_checked_on_empty` | After search with no results, gaps get `last_checked` but not `last_verified` | Edge Case 7, F4.6 |
| `test_pipeline_without_schema_unchanged` | With no schema configured, pipeline behaves exactly as before (backward compatibility) | Regression |
| `test_dead_code_load_search_context_wired` | `load_search_context()` is now called during query decomposition | Seam D from 17-01 |
| `test_all_385_existing_tests_pass` | Full existing test suite passes with no modifications | Regression |

**Estimated commits:** 5 (context refactor, budget enforcement, relevance gate, pre-research check, post-research update)
**Estimated total lines:** ~190 delta (modifications to existing files)

### What it unlocks

- The research agent is now gap-aware: it knows what it knows, what's stale, and what to research next
- Token budgets prevent the #1 risk (F5.2) from ever manifesting
- The state loop is closed: research → findings → persist → next run reads state
- Future cycles can add Google Drive context loading (swap the file reader in context.py, same `ContextResult` API)
- Future cycles can add delta output (state is now persistent, so before/after comparison becomes possible)

---

## What's Deliberately Deferred

These features surfaced in research but are excluded from Cycles 17A-17D because they either have high external dependency risk, depend on the foundation built here, or are lower priority:

| Feature | Why deferred | When it becomes viable |
|---------|-------------|----------------------|
| **Google Drive loading** | Highest external dependency (OAuth, API quotas, format conversion). The `ContextResult` API from 17A is designed so Drive loading slots in by replacing the file reader in context.py — no pipeline changes needed | After 17D. Separate cycle with mocked Drive API tests |
| **Delta-only output** | Requires state persistence (17C) AND the semantic diff problem (F3.2) which the research flags as "fundamentally hard with no clean solution." Attempting it before state persistence is solid would compound risks | After 17D, as a dedicated cycle. Start with structural diff (section-by-section comparison) before attempting semantic diff |
| **Multi-property support** | Requires property-scoped state (17C), property-scoped context loading (17D), and an orchestrator above `ResearchAgent`. Largest scope expansion of any feature | After Drive loading and delta output. The state and context modules from 17A-17D are designed to be parameterized by property path, so the main work is the orchestrator |
| **Fuzzy section matching** | Edge Case 5 recommends starting with exact matching + clear warnings. The `ContextResult` type from 17A provides a natural place to carry section-match warnings | Can be added to context.py at any point after 17D |
| **Automated scheduling** | Research (17-03, F4.3) warns about race conditions with concurrent execution. Single-user manual invocation is safer until locking is in place | After multi-property support and state locking |

---

## Dependency Graph

```
17A: Foundation Infrastructure
 │
 ├──▶ 17B: Gap Schema Layer
 │     │
 │     └──▶ 17C: State Persistence + Staleness
 │           │
 └───────────┴──▶ 17D: Pipeline Integration
                   │
                   ├──▶ Google Drive Loading (future)
                   ├──▶ Delta-Only Output (future)
                   └──▶ Multi-Property Support (future)
```

Each arrow means "depends on." 17D depends on all three prior cycles. Future features depend on 17D.

---

## Risk Mitigation Summary

How each cycle addresses the top-10 failure modes from 17-03:

| Rank | Failure | Addressed in | How |
|------|---------|-------------|-----|
| 1 | F5.2 Context window budget war | **17A** (utility) + **17D** (enforcement) | Token budget with priority-based pruning |
| 2 | F3.2 Semantic diff accuracy | **Deferred** | Foundation must exist first; start with structural diff |
| 3 | F5.1 Error cascade across features | **17A** (exception types) + **17D** (degradation hierarchy) | Distinct error types prevent catch-all swallowing |
| 4 | F1.1 Context overflow from Drive docs | **17A** (token budget) + **Deferred** (Drive loading) | Budget caps context size regardless of source |
| 5 | F4.1 Cascading status flips | **17C** (cascade prevention rule) | Staleness based on gap's own TTL, not dependencies |
| 6 | F2.1 Malformed schema crashes | **17B** (validator) | Parse errors → `SchemaError` with all issues listed |
| 7 | F3.3 Baseline state corruption | **17A** (atomic writes) + **17C** (state writer) | Write-to-temp + rename prevents partial writes |
| 8 | F5.3 Exception hierarchy gaps | **17A** (first commit) | New exception types built before any feature code |
| 9 | F4.4 State file write corruption | **17A** (atomic writes) | Same as F3.3 |
| 10 | F3.4 Context doubling for delta | **17A** (token budget) + **Deferred** (delta) | Budget treats baseline as a component with its own allocation |

---

## Session Feasibility Check

| Cycle | New files | Modified files | Est. lines | Commits | External deps |
|-------|-----------|---------------|-----------|---------|---------------|
| 17A | 3 (`context_result.py`, `token_budget.py`, `safe_io.py`) | 1 (`errors.py`) | ~190 | 4 | None |
| 17B | 1 (`schema.py`) | 0 | ~290 | 4-5 | PyYAML (already common) |
| 17C | 2 (`state.py`, `staleness.py`) | 0 | ~240 | 4-5 | None |
| 17D | 0 | 4 (`context.py`, `synthesize.py`, `relevance.py`, `agent.py`) | ~190 delta | 5 | None |

All cycles are within the 4-5 commit constraint. No cycle exceeds ~300 lines of new code. No cycle requires external service access for testing (Drive is deferred). Each cycle ends with a passing test suite — the existing 385 tests remain untouched until 17D, which explicitly verifies they still pass.
