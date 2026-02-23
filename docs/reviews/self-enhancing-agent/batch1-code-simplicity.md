# Code Simplicity Reviewer — Review Findings

**PR:** Self-Enhancing Agent (self-critique feedback loop)
**Branch:** main (bad292e..57bf44e)
**Date:** 2026-02-23
**Agent:** code-simplicity-reviewer

## Findings

### 1. `CritiqueError` Exception Never Raised (Dead Code)
- **Severity:** P2
- **File:** research_agent/errors.py:48-50
- **Issue:** Defined but never raised anywhere. `evaluate_report` catches errors internally and returns defaults. The `except (CritiqueError, Exception)` in agent.py will never catch a `CritiqueError`.
- **Suggestion:** Remove `CritiqueError`. Simplify the except clause.

### 2. Redundant Exception Catch: `(CritiqueError, Exception)`
- **Severity:** P2
- **File:** research_agent/agent.py:155
- **Issue:** `Exception` already covers `CritiqueError`. The tuple is redundant. Could also remove the try/except entirely since `evaluate_report` handles errors internally.
- **Suggestion:** Simplify to just `except Exception` or remove the outer try/except.

### 3. `overall_pass` Property Unused Outside Aggregation Filter
- **Severity:** P2
- **File:** research_agent/critique.py:58-66
- **Issue:** The pipeline never branches on pass/fail. Only used as a filter in `_summarize_patterns`. The dual gate condition (mean >= 3.0 AND all >= 2) is more complex than needed for a simple "include in aggregation" filter.
- **Suggestion:** Keep for now but flag as simplification candidate. A single `mean >= 3.0` threshold would suffice.

### 4. `query_domain` Field — YAGNI
- **Severity:** P2
- **File:** research_agent/context.py:230, research_agent/critique.py:56
- **Issue:** `load_critique_history` accepts a `domain` parameter but the only caller passes no domain filter. The entire domain extraction, storage, validation, and filtering machinery is built for a hypothetical future use case.
- **Suggestion:** Remove `domain` parameter from `load_critique_history`. Remove `query_domain` from `CritiqueResult`, prompts, parsing, and YAML output. Add later if needed.

### 5. Elaborate Slug Generation for Machine-Consumed Filenames
- **Severity:** P3
- **File:** research_agent/critique.py:248-251
- **Issue:** Human-readable slug generation (replace spaces, regex cleanup, "unknown" fallback) for files only read by `glob + yaml.safe_load`. No human reads these filenames.
- **Suggestion:** Simplify to `critique_{timestamp}.yaml`.

### 6. Over-Defensive `_validate_critique_yaml`
- **Severity:** P2
- **File:** research_agent/context.py:146-173
- **Issue:** 28-line validation function for files the agent itself writes via a frozen dataclass + `yaml.dump`. Only way files could be invalid is manual tampering or disk corruption. Text length checks re-validate constraints already enforced by `evaluate_report`.
- **Suggestion:** Simplify to minimal check: verify it's a dict with expected keys. Skip range/type/length checks.

### 7. `_summarize_patterns` Builds Fragile Natural Language
- **Severity:** P3
- **File:** research_agent/context.py:176-225
- **Issue:** 50 lines of aggregation logic to produce a single paragraph. The `Counter` for recurring weaknesses does exact string matching on LLM-generated free text, which is unreliable for deduplication.
- **Suggestion:** Simplify to just dimension averages and list any below 3.5. Drop recurring weakness counter.

### 8. `scoring_adjustments` Parameter Name is Misleading
- **Severity:** P3
- **File:** research_agent/relevance.py:107, :262
- **Issue:** Name suggests it adjusts scoring thresholds/weights, but it's actually advisory critique-history text appended to the prompt.
- **Suggestion:** Rename to `critique_context` or `scoring_guidance`.

### 9. Critique Context Threaded to 3 Stages Prematurely
- **Severity:** P2
- **File:** research_agent/agent.py:216, :418, :515
- **Issue:** Critique context passed to decompose, relevance, and synthesize — three integration points, three parameter additions, three prompt modifications. Telling the query analyzer about past source diversity scores is unlikely to change sub-query generation meaningfully. Over-engineering for unproven value.
- **Suggestion:** Start with synthesize only. Add decompose/relevance later if data shows it helps.

### 10. `_last_critique` Instance Variable Stored but Never Read
- **Severity:** P2
- **File:** research_agent/agent.py:70, :151
- **Issue:** Set in `_run_critique` and initialized in `__init__` but never read by any production code. State stored for a hypothetical future feature.
- **Suggestion:** Remove `self._last_critique` and its assignment.

### 11. `_critique_context` as Instance State Instead of Local Variable
- **Severity:** P3
- **File:** research_agent/agent.py:71, :192-195
- **Issue:** Set at start of `_research_async`, read in `_evaluate_and_synthesize`. Could be a parameter instead of mutable instance state. The `self._critique_context = None` reset at method top is a code smell.
- **Suggestion:** Pass as parameter through the call chain for explicit data flow.

### 12. Tests Don't Actually Test Agent Behavior
- **Severity:** P2
- **File:** tests/test_critique.py:232-269
- **Issue:** `TestAgentCritiqueHistoryThreading` manually replicates agent logic instead of calling `_research_async`. Tests Python assignment, not agent behavior. Gives false confidence.
- **Suggestion:** Delete these tests or rewrite to call actual agent methods.

### 13. Double Sanitization of Critique Context
- **Severity:** P3
- **File:** research_agent/context.py:225, research_agent/decompose.py:140
- **Issue:** `_summarize_patterns` sanitizes output, then each consumer (decompose, relevance, synthesize) sanitizes again. Idempotent but unnecessary work.
- **Suggestion:** Sanitize once at source, document output is pre-sanitized, remove downstream calls.

### 14. Hardcoded `Path("reports/meta")` in Two Places
- **Severity:** P3
- **File:** research_agent/agent.py:149, :193
- **Issue:** Same hardcoded relative path appears twice. Not configurable, CWD-dependent.
- **Suggestion:** Extract to constant or constructor parameter.

### 15. `_MIN_CRITIQUES_FOR_GUIDANCE = 3` Cold Start
- **Severity:** P3
- **File:** research_agent/context.py:137
- **Issue:** Requires 3 passing critiques before feedback activates. Feature is inert for first 3 runs. No override for testing/bootstrapping.
- **Suggestion:** Keep as-is. Just be aware during testing.

## Summary
- P1 (Critical): 0
- P2 (Important): 7
- P3 (Nice-to-have): 8

**Estimated removable LOC:** ~120-150 lines by removing `CritiqueError`, `query_domain` machinery, `_last_critique`, over-engineering in validation, useless tests, and consolidating critique context to synthesize only.
