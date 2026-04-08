---
cycle: 29H
title: "Codebase Hygiene — Audit-Driven Fixes"
brainstorm: "N/A — 6-agent comprehensive audit served as brainstorm (architecture, security, performance, Python quality, patterns, simplicity)"
roadmap: "docs/research/2026-03-09-entropy-fixes-roadmap.md"
feed_forward:
  risk: "A/B live validation for cutoff raise not yet run — if production queries show unexpected insufficient_data at cutoff=4, check score-3 clustering"
  verify_first: false
---

# Cycle 29H Plan: Codebase Hygiene — Audit-Driven Fixes

**Date:** 2026-04-07
**Sessions:** 5
**Relationship to entropy roadmap:** This is a parallel housekeeping cycle. It does NOT replace Cycle 29 (skeptic enforcement + evidence-tier labeling). Run this first — several fixes (gate decision enum, type cleanup, exception consolidation) make the Cycle 29 feature work cleaner.

## Prior Phase Risk

> "Least confident about? A/B live validation not yet run. Code analysis supports the raise, but no live Haiku scores at cutoff=4 observed."

**Accepted.** This hygiene cycle does not touch relevance scoring. The cutoff change ships as-is. If live queries surface problems, the gate decision enum from Session 1 will make debugging faster.

## What is changing?

14 P2 findings and select P3 items from a 6-agent comprehensive audit, organized into 5 sessions by dependency order. Total estimated change: ~250 lines modified/removed across 12 files. No new features — only type safety, deduplication, defense-in-depth, and dead code removal.

## What must NOT change?

- Pipeline behavior: all 987 tests must pass after every session
- Report output: no visible change to generated reports
- Mode configurations: no threshold or parameter changes
- API call count: total API calls per run is unchanged — **exception:** Session 5d may route more URLs through Tavily Extract when `extract_domains` is configured; when no context is loaded, Tavily Extract is skipped entirely (zero new API calls)
- API burst rate: Session 5a raises concurrency limits, increasing the peak request rate within batch windows. Total call count is unchanged, but burst rate rises. The existing `process_in_batches` reactive backoff (sleep only on 429, then clear) handles this. **Acceptance condition:** smoke test on the user's current API tier completes without sustained 429 cascades. If 429s increase noticeably, revert to previous constants — this is a 1-line change per file.
- MCP server interface: all existing tools remain functional

## How will we know it worked?

1. All 987 existing tests pass after each session
2. New tests added for `report_store.py` (Session 4)
3. `mypy --strict` on modified files shows no new errors (if mypy is available)
4. Manual smoke test: `python3 main.py --quick "best pizza in NYC"` produces a normal report

## Most likely way this plan is wrong?

Two risks: (1) The synthesis exception consolidation (Session 2) could subtly change error messages if the context manager doesn't preserve the exact same exception wrapping — mitigate by comparing before/after exception messages in tests. (2) Session 5a concurrency tuning could trigger 429 cascades on lower-tier Anthropic API plans — mitigate by smoke testing after the change and keeping the revert path to 1 line per file.

---

## Session 1: Type Safety Foundation

**Theme:** Replace stringly-typed patterns with enums and proper type annotations. These are root-cause fixes that make Sessions 2-5 safer.

**Files:** `relevance.py`, `agent.py`, `results.py`, `errors.py`

### 1a. Gate decision enum

Create `GateDecision` as a `StrEnum` (Python 3.11+) or `Literal` type:

```python
# In relevance.py (or a new section of errors.py)
from enum import StrEnum

class GateDecision(StrEnum):
    FULL_REPORT = "full_report"
    SHORT_REPORT = "short_report"
    INSUFFICIENT_DATA = "insufficient_data"
    NO_NEW_FINDINGS = "no_new_findings"
```

Replace all 12+ bare string comparisons across `relevance.py`, `agent.py`, and `results.py`.

**Public API:** Export `GateDecision` from `research_agent/__init__.py` and add to `__all__`. Consumers need it to compare `result.status` against typed values. Backward-compatible: `StrEnum` is a `str` subclass, so `result.status == "full_report"` still works.

### 1b. Fix `dropped_sources` type annotation

Change `RelevanceEvaluation.dropped_sources` from bare `tuple` to `tuple[SourceScore, ...]`.

Remove the dead `isinstance(src, dict)` branch in `_urls_from_evaluation` (`agent.py:232-249`). This branch is unreachable after Cycle 28's conversion in `evaluate_sources`.

### 1c. Extract `ANTHROPIC_ERRORS` tuple

Add to `errors.py`:
```python
ANTHROPIC_ERRORS = (APIError, RateLimitError, APIConnectionError, APITimeoutError)
```

Replace the identical tuple in 10+ exception handlers across `decompose.py`, `search.py`, `synthesize.py`, `skeptic.py`, `context.py`, `critique.py`.

### 1d. Extract gate decision logic (including rationale)

The full/short/insufficient decision tree exists in both `evaluate_sources` (`relevance.py:356-381`) and `_try_coverage_retry` (`agent.py:775-788`). Both build a `decision` string AND a `decision_rationale` string, but the rationale formats diverge:

- `evaluate_sources` builds verbose rationales with `mode.relevance_cutoff`, `mode.name`, threshold values
- `_try_coverage_retry` builds terse rationales like `"5/8 sources passed after retry merge"`

**Decision:** The extracted helper `compute_gate_decision()` returns a `(GateDecision, str)` tuple — the decision enum and the rationale string. It takes `survived_count`, `total_count`, `mode`, and an optional `context: str = ""` parameter. The context string (e.g., `"after retry merge"`) is appended to the rationale, preserving the existing distinction between first-pass and retry rationale wording without duplicating the threshold logic.

Signature:
```python
def compute_gate_decision(
    survived: int,
    total: int,
    mode: ResearchMode,
    context: str = "",
) -> tuple[GateDecision, str]:
```

Both call sites (`evaluate_sources` and `_try_coverage_retry`) switch to this helper. `evaluate_sources` passes no context (gets the verbose default). `_try_coverage_retry` passes `context="after retry merge"`.

**Estimated size:** ~60 lines changed, ~20 lines removed
**Tests:** Existing tests cover all gate paths. Add 3 tests for `compute_gate_decision` directly: one per decision branch, plus one verifying context suffix.

---

## Session 2: Synthesis Deduplication

**Theme:** Consolidate the 4x duplicated exception handling in `synthesize.py` (3 complete + 1 incomplete).

**Files:** `synthesize.py`

### 2a. Synthesis exception context manager

Create a context manager that wraps the streaming API call:

```python
@contextmanager
def _synthesis_errors(label: str = "Synthesis"):
    """Convert Anthropic API errors to SynthesisError."""
    try:
        yield
    except RateLimitError as e:
        raise SynthesisError(f"{label} rate limited: {e}")
    except APITimeoutError as e:
        raise SynthesisError(f"{label} timed out: {e}")
    except APIConnectionError as e:
        raise SynthesisError(f"{label} connection error: {e}")
    except APIError as e:
        raise SynthesisError(f"{label} API error: {e}")
    except (SynthesisError, KeyboardInterrupt):
        raise
    except (httpx.TransportError, ValueError) as e:
        raise SynthesisError(f"{label} failed: {e}")
```

**Scope — 4 functions, not 3.** Apply in:
- `synthesize_report` (lines 368-379) — `_synthesis_errors("Report synthesis")`
- `synthesize_draft` (lines 481-492) — `_synthesis_errors("Draft synthesis")`
- `synthesize_final` (lines 721-732) — `_synthesis_errors("Final synthesis")`
- `synthesize_mini_report` (lines 846-853) — `_synthesis_errors("Mini-report")`

`synthesize_mini_report` currently has **incomplete** exception handling: it catches only 4 Anthropic exceptions and is missing the `(SynthesisError, KeyboardInterrupt)` re-raise and the `(httpx.TransportError, ValueError)` catch. Applying the shared context manager fixes this gap as a side effect.

The `label` parameter preserves the existing per-function prefixes (e.g., "Mini-report rate limited") so error messages remain distinguishable in logs.

Note: After Session 1c ships `ANTHROPIC_ERRORS`, this context manager can use that tuple instead of listing individual exception types. But the context manager still adds value because it includes the `SynthesisError` wrapping with specific messages per type — keep both.

### 2b. Update stale idempotency comment

`synthesize.py:551` says `sanitize_content` is not idempotent. It has been idempotent since Cycle 27. Update the comment to:
```python
# draft is LLM output from synthesize_draft — trusted content, not web-sourced.
# No need to re-sanitize even though sanitize_content() is now idempotent (C27).
```

**Estimated size:** ~48 lines removed, ~15 lines added (net -33)
**Tests:** Existing synthesis tests cover all three functions. Verify error messages match.

---

## Session 3: Security Hardening & Module Hygiene

**Theme:** Close defense-in-depth gaps and clean up cross-module coupling.

**Files:** `sanitize.py`, `context.py`, `cascade.py`, `fetch.py`, `search.py`, `skeptic.py`

### 3a. Null byte stripping in `sanitize_content`

Add `text = text.replace("\x00", "")` to `sanitize_content()` before the `html.unescape` call. One line, defense-in-depth.

### 3b. Sanitize `_summarize_patterns` return value

In `context.py`, wrap the final return of `_summarize_patterns()` with `sanitize_content()`. Individual weakness strings are already sanitized, but the assembled summary string is not. Closes the one gap in the "all content entering prompts is sanitized" invariant.

### 3c. Promote private cross-module functions

- Rename `_is_safe_url` to `is_safe_url` in `fetch.py` (update all call sites)
- Rename `_get_tavily_client` to `get_tavily_client` in `search.py` (update cascade.py import)
- These are genuinely cross-module APIs and should not have underscore prefixes

### 3d. Pre-check httpx transport internals before patching

In `fetch.py`, **before** the `transport._pool._network_backend = _SSRFSafeBackend()` assignment, add an explicit pre-check with a real exception (not an assert, which can be stripped by `-O`):

```python
if not hasattr(transport, '_pool') or not hasattr(transport._pool, '_network_backend'):
    raise RuntimeError(
        f"httpx {httpx.__version__} internals changed: "
        "transport._pool._network_backend not found. "
        "SSRF protection cannot be applied. Pin httpx to a compatible version."
    )
transport._pool._network_backend = _SSRFSafeBackend()  # noqa: SLF001
```

This turns a silent security failure into a loud crash on httpx upgrades. Uses `RuntimeError` (not `assert`) so it fires even under `python -O`.

### 3e. Thread-safe Tavily client cache

Replace the 3 module-level globals in `search.py:36-38` with a `threading.Lock`-guarded cache or `functools.lru_cache`.

### 3f. Remove `_build_context_block` passthrough

Delete the trivial wrapper in `skeptic.py:42-44` and use the imported `build_context_block` directly at call sites.

**Estimated size:** ~20 lines added, ~15 lines removed
**Tests:** Add 1 test for null byte stripping. Existing tests cover the rest.

---

## Session 4: Test Coverage & CLI Fixes

**Theme:** Fill test gaps and fix user-facing issues.

**Files:** `report_store.py`, `cli.py`, new `tests/test_report_store.py`

### 4a. Add `test_report_store.py` — targeted gap coverage only

`tests/test_main.py` already has thorough coverage for `sanitize_filename` (7 tests, lines 25-50) and `get_auto_save_path` (5 tests, lines 53-85). **Do not duplicate these.**

The new `test_report_store.py` covers only the two untested functions:

**`_resolves_within_reports_root`** (~5 tests):
- Path inside reports/ returns True
- `../` traversal returns False
- Absolute path outside reports/ returns False
- Symlink pointing outside reports/ returns False (security-critical)
- Non-existent path inside reports/ returns True (strict=False behavior)

**`get_reports`** (~5 tests):
- Non-existent reports directory returns empty list
- Empty directory returns empty list
- Directory with valid .md files returns sorted ReportInfo list (newest first)
- Files matching _OLD_FORMAT and _NEW_FORMAT regex are both parsed
- Non-standard filenames fall back to filename as query_name with date=""

Target: ~10 tests (not 15-20).

### 4b. Fix stale CLI help text

`cli.py:130-143` hardcodes outdated source counts and costs (`--quick` says "3 sources", actual is 4; `--standard` says "7 sources", actual is 10). Update the hardcoded strings to match current `ResearchMode` factory values. Keep them as string literals — reading from mode objects at argument parse time adds unnecessary coupling for help text.

**Estimated size:** ~40 lines added (tests), ~10 lines changed (CLI)
**Tests:** New test file is the deliverable.

---

## Session 5: Simplification & Performance

**Theme:** Remove dead code, simplify patterns, tune concurrency constants.

**Files:** `agent.py`, `summarize.py`, `relevance.py`, `modes.py`, `cascade.py`

### 5a. Performance quick wins (concurrency tuning)

- Raise `MAX_CONCURRENT_CHUNKS` from 3 to 5 in `summarize.py:35`
- Raise `BATCH_SIZE` from 5 to 10 in `relevance.py:26`

Two 1-line changes. Saves ~7-15 seconds on standard-mode runs.

**Rate-limit impact:** These increase peak burst rate within batch windows (5 concurrent summarize calls instead of 3; 10 concurrent scoring calls instead of 5). Total API call count per run is unchanged. The existing `process_in_batches` reactive backoff (sleep only on 429, then clear event) already handles bursts. **Acceptance check:** run `python3 main.py --standard "best pizza in NYC"` after the change — if the run completes without noticeably more 429-retry log lines than before, the constants are safe. If 429s increase, revert to previous values (1-line change per file, zero risk).

### 5b. Use `contextlib.nullcontext` in `summarize_content`

Replace the duplicate summarize_chunk branches (with/without semaphore) with:
```python
async with (semaphore if semaphore else contextlib.nullcontext()):
    return await summarize_chunk(...)
```

### 5c. Inline `_build_instruction_list`

Replace the 14-line function in `relevance.py:55-68` (called once) with an inline instruction string at the call site.

### 5d. Move `EXTRACT_DOMAINS` to context profile configuration

**Problem:** `cascade.py:30-39` hardcodes 8 Pacific-Flow-specific domains. This makes Tavily Extract (layer 2) dead code for all non-PFE research topics.

**Replacement contract:**

1. **New field on `ContextProfile`** (`context_result.py:35-48`):
   ```python
   extract_domains: tuple[str, ...] = ()
   ```
   Empty tuple = no Tavily Extract domains configured.

2. **Parse in `context.py`** — add to `_parse_template()` alongside `blocked_domains`:
   ```yaml
   # In context YAML frontmatter:
   extract_domains:
     - weddingwire.com
     - theknot.com
   ```
   Parsing follows the same pattern as `blocked_domains`: read list, convert to tuple, per-field try/except.

3. **Thread to `cascade.py`** — `cascade_recover()` already receives the full pipeline context. Add `extract_domains: tuple[str, ...] = ()` parameter. `_is_extract_domain()` checks against the passed tuple instead of the module-level frozenset. Delete the `EXTRACT_DOMAINS` constant.

4. **Thread from `agent.py`** — `_fetch_extract_summarize()` passes `self._run_context.profile.extract_domains` to `cascade_recover()`.

**Fallback behavior when no context is loaded:**
- `ContextProfile()` default → `extract_domains = ()`
- `_is_extract_domain()` with empty tuple → always returns False
- **Layer 2 (Tavily Extract) is skipped entirely** → URLs fall through to Layer 3 (snippet fallback)
- **This matches current behavior for non-PFE queries** — today, non-PFE URLs already skip layer 2 because they don't match `EXTRACT_DOMAINS`

**Cost/API invariant:** When no context is loaded, **zero Tavily Extract API calls** — same as today. When a context with `extract_domains` is loaded, Tavily Extract fires for matching URLs only — same as today. The only change is where the domain list lives, not when it fires.

**Affected files:** `context_result.py` (1 field), `context.py` (~8 lines parse logic), `cascade.py` (~10 lines parameter threading + delete constant), `agent.py` (~2 lines pass-through)

**Existing PFE context files:** Update any context YAML files in `contexts/` to include `extract_domains:` with the 8 domains currently hardcoded. If no PFE context files exist, document in the commit message that PFE users need to add the field.

### 5e. Blocked-domain helper method

Extract the 4-line blocked-domain filter (copy-pasted in `_research_with_refinement` and `_research_deep`) into a `_filter_blocked(results)` helper on `ResearchAgent`.

**Estimated size:** ~30 lines removed, ~15 lines added
**Tests:** Existing tests cover all paths. Verify performance constants don't break rate limits.

---

## Session Summary

| Session | Theme | Files | Net LOC |
|---------|-------|-------|---------|
| 1 | Type safety foundation | relevance.py, agent.py, results.py, errors.py | -20 |
| 2 | Synthesis deduplication (4 functions) | synthesize.py | -40 |
| 3 | Security hardening & module hygiene | sanitize.py, context.py, cascade.py, fetch.py, search.py, skeptic.py | +5 |
| 4 | Test coverage (targeted) & CLI fixes | cli.py, new tests/test_report_store.py | +50 |
| 5 | Simplification & performance | agent.py, summarize.py, relevance.py, cascade.py, context_result.py, context.py | -5 |
| **Total** | | **14 files** | **~-10** |

---

## Plan Quality Gate

| Question | Answer |
|----------|--------|
| What exactly is changing? | 14 P2 findings: type safety (enum, annotations, rationale preservation), deduplication (exception handling across 4 synthesis functions), security hardening (sanitization, SSRF pre-check), test coverage (_resolves_within_reports_root, get_reports), CLI accuracy, performance tuning (concurrency constants — wall-clock time only, not API calls), dead code removal, EXTRACT_DOMAINS move to context profile |
| What must not change? | Pipeline behavior, report output, total API call count (Session 5d: zero Tavily Extract calls when no context loaded — same as today), mode thresholds, MCP interface. Session 5a increases burst rate but not call count — existing 429 backoff handles this; revert path is 1 line per file. |
| How will we know it worked? | 987+ tests pass, ~10 new report_store tests pass, smoke test produces normal report without sustained 429s, PFE context files updated with extract_domains |
| Most likely way this plan is wrong? | (1) Synthesis exception consolidation could change error message format (mitigated by `label` parameter). (2) `compute_gate_decision` could lose rationale detail if `context` parameter doesn't capture the verbose/terse distinction. (3) Session 5a burst rate increase could trigger 429 cascades on lower-tier API plans (mitigated by smoke test + 1-line revert). |

## Feed-Forward

- **Hardest decision:** Whether to run this before or alongside entropy Cycle 29. Chose before — the gate decision enum and type cleanup directly simplify the skeptic enforcement work in C29.
- **Rejected alternatives:** (1) Merging hygiene into C29 feature work — rejected because mixing cleanup with feature changes makes review harder. (2) Skipping the `EXTRACT_DOMAINS` move — it's YAGNI but also makes the cascade Pacific-Flow-specific, which limits reuse. (3) Having Tavily Extract fire for ALL domains when no context is loaded — rejected because it would increase API costs and violate the "no new API calls" invariant.
- **Least confident:** The `compute_gate_decision` rationale extraction (Session 1d). The current `evaluate_sources` rationale includes mode-specific detail (`relevance_cutoff`, threshold values) while `_try_coverage_retry` uses terse "after retry merge" phrasing. The `context` parameter approach preserves the distinction, but the exact rationale wording may need adjustment during implementation to keep log messages equally useful for debugging.
