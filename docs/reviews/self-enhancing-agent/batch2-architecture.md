# Architecture Strategist — Review Findings

**PR:** Self-Enhancing Agent (self-critique feedback loop)
**Branch:** main (bad292e..57bf44e)
**Date:** 2026-02-23
**Agent:** architecture-strategist

## Findings

### 1. Bare `except Exception` in `_run_critique`
- **Severity:** P2
- **File:** research_agent/agent.py:155
- **Issue:** `except (CritiqueError, Exception)` effectively becomes bare `except Exception`. Violates project convention. `CritiqueError` in the tuple is redundant.
- **Suggestion:** Replace with specific exceptions: `(CritiqueError, OSError, yaml.YAMLError)` or the specific API error types.

### 2. Hardcoded `Path("reports/meta")` in Two Places
- **Severity:** P2
- **File:** research_agent/agent.py:149, :193
- **Issue:** Relative path hardcoded twice, CWD-dependent, not configurable. Inconsistent with how `schema_path` is handled via constructor.
- **Suggestion:** Extract to module-level constant `META_DIR = Path("reports/meta")` or derive from existing configuration.

### 3. `_critique_context` as Mutable Instance State
- **Severity:** P2
- **File:** research_agent/agent.py:71
- **Issue:** Stored as instance variable but only valid during a single `_research_async` call. Leaks between calls if agent is reused. Other context values are local variables. Pattern is fragile — relies on resetting at line 192.
- **Suggestion:** Make it a local variable in `_research_async` and pass explicitly to `_evaluate_and_synthesize` as a parameter.

### 4. Threading Critique Context Modifies 3 Existing Signatures
- **Severity:** P3
- **File:** research_agent/decompose.py:105, research_agent/relevance.py:107, research_agent/synthesize.py:365
- **Issue:** Strictly reading the "additive pattern" principle, modifying three existing module signatures is not purely additive. However, the changes are minimal (one optional parameter each) and backward-compatible.
- **Suggestion:** Acceptable as-is. If more cross-cutting concerns are added, consider a `PipelineContext` dataclass that carries all advisory data.

### 5. Inconsistent Parameter Naming Across Stages
- **Severity:** P3
- **File:** research_agent/decompose.py:105, research_agent/relevance.py:107, research_agent/synthesize.py:365
- **Issue:** Same data called `critique_context`, `scoring_adjustments`, and `lessons_applied` across three stages. All fed from `self._critique_context`. Obscures data lineage.
- **Suggestion:** Unify on a single name like `critique_guidance` across all stages.

### 6. `CritiqueError` Defined but Never Raised
- **Severity:** P3
- **File:** research_agent/errors.py:48-50
- **Issue:** Dead code in exception hierarchy. No code path raises it. The catch clause will never actually catch a `CritiqueError`.
- **Suggestion:** Either raise it from critique functions (wrapping underlying errors) or remove it.

### 7. Critique Evaluates Process Metadata, Not Report Text
- **Severity:** P3
- **File:** research_agent/critique.py:162-185
- **Issue:** Prompt instructs Claude to "Score the research run's process" and only provides metadata (counts, gate decision, skeptic summary). Never sees the report. Limits the value of `claim_support` and `coverage` dimensions.
- **Suggestion:** Design trade-off — document the limitation. Consider adding truncated report text (500-1000 tokens) if you want content-based assessment.

### 8. Double Sanitization of Critique Data
- **Severity:** P3
- **File:** research_agent/context.py:224-225
- **Issue:** `_summarize_patterns` sanitizes output, then each consumer (decompose, relevance, synthesize) sanitizes again. Harmless but creates double-encoding (`<` becomes `&amp;lt;`).
- **Suggestion:** Minor — either trust write-time sanitization or add a comment noting double-encoding is intentional.

### 9. No Test for `save_critique` Raising `OSError`
- **Severity:** P3
- **File:** tests/test_critique.py:220-229
- **Issue:** Only tests `CritiqueError` from `evaluate_report`. No test for `save_critique` failing with `OSError` (disk full, permission denied). Important if exception handler is tightened.
- **Suggestion:** Add a test where `evaluate_report` succeeds but `save_critique` raises `OSError`.

## Summary
- P1 (Critical): 0
- P2 (Important): 3
- P3 (Nice-to-have): 6
