# Codebase Hygiene: Audit-Driven Fixes (Cycle 29H)

**Date:** 2026-04-07
**Cycle:** 29H (parallel to entropy roadmap, not a replacement)
**Trigger:** 6-agent comprehensive audit (architecture, security, performance, Python quality, patterns, simplicity)
**Sessions:** 5 implementation + 1 review fix

## Problem

After 28 development cycles, the codebase had accumulated 14 P2 findings across type safety, exception handling, security defense-in-depth, test coverage, and dead code. No individual finding was urgent, but collectively they increased maintenance cost and masked the real data flow (e.g., `dropped_sources: tuple` hiding that it was always `tuple[SourceScore, ...]`).

## Solution

Five sessions, dependency-ordered so each builds on the previous:

### Session 1: Type Safety Foundation
- **`GateDecision` StrEnum** in `errors.py` — replaces 12+ bare `"full_report"` / `"short_report"` string comparisons with typed enum values. Typo → import error instead of silent wrong branch.
- **`compute_gate_decision()`** extracted to `relevance.py` — returns `(GateDecision, str)` tuple. `verbose=True` (default) for `evaluate_sources` produces threshold-rich rationale. `verbose=False` for `_try_coverage_retry` produces terse `"5/8 sources passed after retry merge"` format. Eliminates duplicated 15-line decision tree.
- **`ANTHROPIC_ERRORS`** tuple constant in `errors.py` — defined but not yet consumed at all 10+ call sites (deferred to avoid bloating the cycle).
- **`dropped_sources: tuple[SourceScore, ...]`** — typed correctly, dead `isinstance(src, dict)` branch removed.

### Session 2: Synthesis Exception Deduplication
- **`_synthesis_errors(label)`** context manager — wraps all 4 synthesis functions (`synthesize_report`, `synthesize_draft`, `synthesize_final`, `synthesize_mini_report`). The `label` parameter preserves per-function error message prefixes.
- **Bug found:** `synthesize_mini_report` had incomplete exception handling (missing `(SynthesisError, KeyboardInterrupt)` re-raise and `(httpx.TransportError, ValueError)` catch). Fixed as a side effect of applying the shared context manager.

### Session 3: Security Hardening & Module Hygiene
- **Null byte stripping** in `sanitize_content()` — defense-in-depth.
- **`_summarize_patterns()` return sanitized** — closed the one gap in the "all content entering prompts is sanitized" invariant.
- **Public API promotion** — `_is_safe_url` → `is_safe_url`, `_get_tavily_client` → `get_tavily_client`. Cross-module APIs should not have underscore prefixes.
- **httpx SSRF pre-check** — `RuntimeError` (not `assert`) before patching `transport._pool._network_backend`. Fires under `python -O`.
- **Thread-safe Tavily client cache** — `threading.Lock` guards the 3 module-level globals. Required autouse test fixtures to reset between tests.
- **Removed `_build_context_block` passthrough** in `skeptic.py` — used `build_context_block` directly.

### Session 4: Test Coverage & CLI
- **10 new tests** in `test_report_store.py` — targeted coverage for `_resolves_within_reports_root` (traversal, symlink, absolute path) and `get_reports` (empty dir, both filename formats, non-standard fallback).
- **CLI help text corrected** — `--quick` 3→4 sources, `--standard` 7→10 sources, costs updated.

### Session 5: Simplification & Performance
- **Concurrency tuning** — `MAX_CONCURRENT_CHUNKS` 3→5, relevance `BATCH_SIZE` 5→10. Wall-clock savings ~7-15s per standard run.
- **`contextlib.nullcontext`** replaced duplicate semaphore branching in `summarize_content`.
- **Inlined `_build_instruction_list`** at its single call site.
- **`EXTRACT_DOMAINS` → context profile** — moved 8 hardcoded Pacific-Flow domains to `extract_domains` field on `ContextProfile`. No-context fallback: empty tuple = layer 2 skipped entirely (zero Tavily Extract API calls).
- **`_filter_blocked()` helper** — replaced 3 copy-pasted 4-line filter blocks.

## Key Patterns

### 1. Audit-Then-Fix Is Better Than Fix-While-Building
Running 6 specialized agents in parallel produced a deduplicated, priority-ordered finding list in ~3 minutes. This is more thorough than catching issues during feature work, where you only see what's in your current context window.

### 2. verbose/terse Rationale Split > Suffix Appending
The initial `context="after retry merge"` suffix approach produced verbose rationale + suffix, which isn't how the retry path originally worked. A `verbose: bool` parameter with two private helpers (`_gate_decision_verbose`, `_gate_decision_terse`) preserves both formats without coupling them.

### 3. Thread-Safe Cache = Autouse Test Fixtures
Making `_get_tavily_client` thread-safe with `threading.Lock` broke 2 test files because the cached client persisted across tests. Lesson: any module-level cache change needs corresponding test isolation. The autouse fixture pattern (`_reset_tavily_cache`) is the standard fix.

### 4. Context Manager for Exception Wrapping Catches Gaps
When consolidating 4 exception blocks into one context manager, we discovered `synthesize_mini_report` was missing 2 exception clauses. The deduplication wasn't just cleanup — it fixed a real gap.

### 5. Fail-Closed Pre-Check > Post-Assignment Assert
`assert` can be stripped by `python -O`. A pre-check `if not hasattr(...): raise RuntimeError(...)` is the correct pattern for security-critical invariants that must hold in all execution modes.

## Risk Resolution

| Flagged Risk | What Happened | Lesson |
|---|---|---|
| Synthesis exception consolidation could change error messages | `label` parameter preserves per-function prefixes. Tests verify. | Parameterized context managers are the right abstraction for "same structure, different labels." |
| `compute_gate_decision` could lose rationale detail | Initial suffix approach was wrong — review caught it. Split into verbose/terse with exact string shape tests. | Don't just append to a verbose format when the original was a different shape. Test the exact output. |
| Session 5a burst rate could trigger 429 cascades | Not yet validated with live queries. Existing `process_in_batches` reactive backoff is the safety net. | Concurrency tuning needs a live smoke test before the cycle is fully closed. |
| Thread-safe cache could break tests | It did — 2 test files needed autouse reset fixtures. | Module-level cache changes always need test isolation review. |
| EXTRACT_DOMAINS removal could change API cost | No-context default = empty tuple = skip layer 2. Matches prior behavior for non-PFE queries. PFE context file updated. | When moving hardcoded config to per-context, the no-config fallback must match the prior default behavior. |

## Metrics

- **Commits:** 7 (5 sessions + 1 HANDOFF + 1 review fix)
- **Tests:** 987 → 1040 (+53 net, including 10 new report_store, 5 gate decision, 2 SSRF, 7 terse rationale, plus test updates)
- **Net LOC:** ~-10 (more code removed than added despite new tests)
- **P2 findings resolved:** 14/14
- **Bugs found during dedup:** 1 (synthesize_mini_report incomplete exception handling)

## Three Questions

1. **Hardest pattern to extract from the fixes?** The verbose/terse rationale split. The first attempt (suffix approach) was wrong — it produced verbose text + terse suffix, which is neither format. The review caught it. The lesson is that when two call sites produce structurally different text from the same decision logic, you need two format functions, not one function with a modifier.
2. **What did you consider documenting but left out?** The f-string logger calls (P3 finding) — converting 7 `logger.warning(f"...")` to `%s` formatting. Left out because it's a style consistency fix with negligible performance impact, not a pattern worth preserving.
3. **What might future sessions miss that this solution doesn't cover?** The `ANTHROPIC_ERRORS` tuple is defined but only consumed in the synthesis context manager. The remaining 10+ inline exception tuples still exist. A future session doing a mechanical find-and-replace might not realize the synthesis functions already use the context manager (which has its own exception list) and try to also replace those — creating a double-handling situation.
