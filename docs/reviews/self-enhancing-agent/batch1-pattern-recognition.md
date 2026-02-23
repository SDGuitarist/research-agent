# Pattern Recognition Specialist — Review Findings

**PR:** Self-Enhancing Agent (self-critique feedback loop)
**Branch:** main (bad292e..57bf44e)
**Date:** 2026-02-23
**Agent:** pattern-recognition-specialist

## Findings

### 1. Bare `except Exception` Violates Project Convention
- **Severity:** P1
- **File:** research_agent/agent.py:155
- **Issue:** `except (CritiqueError, Exception) as e:` catches everything. `CritiqueError` in the tuple is redundant. Violates CLAUDE.md rule: "Never bare `except Exception`".
- **Suggestion:** Catch only specific exception types.

### 2. Duplicated Dimension Constants Across Modules
- **Severity:** P2
- **File:** research_agent/critique.py:25-30, research_agent/context.py:146-173
- **Issue:** The five critique dimensions (`source_diversity`, `claim_support`, `coverage`, `geographic_balance`, `actionability`) are listed independently in `CritiqueResult` fields, the prompt template, the YAML parser, and the validation function. Adding a dimension requires changes in 4+ places.
- **Suggestion:** Define dimension names in a single constant (e.g., `CRITIQUE_DIMENSIONS`) and derive fields/validation from it.

### 3. Duplicated Scores Tuple in CritiqueResult
- **Severity:** P3
- **File:** research_agent/critique.py:58-74
- **Issue:** Both `overall_pass` and `mean_score` construct identical `scores` tuples independently. DRY violation within a small class.
- **Suggestion:** Extract a private `_scores` property.

### 4. Hardcoded `Path("reports/meta")` Repeated
- **Severity:** P2
- **File:** research_agent/agent.py:149, :193
- **Issue:** Same hardcoded relative path appears twice, not configurable, not consistent with how other paths (e.g. `schema_path`) are handled.
- **Suggestion:** Extract to constant or constructor parameter.

### 5. Unused `critique_context` Parameter in `score_source`
- **Severity:** P3
- **File:** research_agent/relevance.py:107
- **Issue:** The parameter `scoring_adjustments` is passed to the prompt but it's unclear if the LLM actually uses it meaningfully for individual source scoring (vs. overall evaluation).
- **Suggestion:** Verify this parameter actually influences scoring quality; otherwise remove from `score_source`.

### 6. f-string Logger Anti-Pattern
- **Severity:** P3
- **File:** research_agent/agent.py:156, research_agent/context.py:265-269
- **Issue:** Uses f-strings in logger calls instead of lazy `%s` formatting.
- **Suggestion:** Use `logger.warning("Self-critique failed: %s", e)`.

### 7. Missing Docstring for `critique_context` Parameter
- **Severity:** P3
- **File:** research_agent/decompose.py:106-123
- **Issue:** New `critique_context` parameter not documented in docstring.
- **Suggestion:** Add to Args block.

### 8. Convoluted Threshold Logic in `load_critique_history`
- **Severity:** P3
- **File:** research_agent/context.py:228-270
- **Issue:** Complex flow: glob files → filter valid YAML → pass to summarize → summarize filters again by `overall_pass` → check count threshold → return loaded/empty/not_configured. The double filtering (first in `load_critique_history` for valid YAML, then in `_summarize_patterns` for passing) is confusing.
- **Suggestion:** Either pre-filter by `overall_pass` in `load_critique_history`, or merge the logic.

### 9. Dead `CritiqueError` Exception Class
- **Severity:** P2
- **File:** research_agent/errors.py:48-50
- **Issue:** Defined and caught but never raised anywhere. Creates false sense of structured error handling.
- **Suggestion:** Remove until actually needed, or have critique functions raise it.

### 10. Same Data Threaded Under Three Different Parameter Names
- **Severity:** P2
- **File:** research_agent/agent.py:216, :418, :515
- **Issue:** `self._critique_context` passed as `critique_context` to decompose, `scoring_adjustments` to relevance, and `lessons_applied` to synthesize. The three different names obscure that it's the same data.
- **Suggestion:** Use a consistent parameter name like `critique_guidance` across all three stages.

### 11. Inconsistent XML Tag Naming for Critique Guidance
- **Severity:** P3
- **File:** research_agent/decompose.py:142-144, research_agent/synthesize.py:485, research_agent/relevance.py:136
- **Issue:** Same data injected with different XML tags: `<critique_guidance>`, `<lessons_applied>`, and no XML tags at all in relevance (just `SCORING CONTEXT:`). Inconsistent with project's XML boundary defense layer.
- **Suggestion:** Wrap in XML tags consistently. Use a common tag name everywhere.

### 12. Test Fixture `mock_async_response` Duplicated
- **Severity:** P3
- **File:** tests/test_relevance.py:104-110, :457-463
- **Issue:** Identical fixture defined in two test classes in the same file.
- **Suggestion:** Move to module-level or conftest.py.

### 13. Test Reimplements Agent Logic Instead of Testing It
- **Severity:** P3
- **File:** tests/test_critique.py:235-255
- **Issue:** Test manually assigns `agent._critique_context = critique_ctx.content` instead of calling the actual agent method. Tests Python assignment, not agent behavior.
- **Suggestion:** Test actual async method or extract critique loading into testable helper.

### 14. `TestLoadContext` Duplicated Across Test Files
- **Severity:** P3
- **File:** tests/test_decompose.py:17-45, tests/test_context.py:69-104
- **Issue:** Nearly identical test classes testing `load_full_context` in both files. Comment in test_decompose.py says "moved to context module" but tests weren't removed.
- **Suggestion:** Remove `TestLoadContext` from `test_decompose.py`.

### Positive: Graceful Degradation Pattern
- **Severity:** (Positive)
- **File:** research_agent/agent.py:126-156, research_agent/critique.py:187-204
- **Issue:** Not an issue — critique pipeline correctly follows project's "additive pattern" principle. Never crashes main pipeline. Quick mode skips entirely.

### Positive: Three-Layer Prompt Injection Defense
- **Severity:** (Positive)
- **File:** research_agent/critique.py:140, :155-159, :162-185
- **Issue:** Not an issue — `evaluate_report` correctly applies all three defense layers: sanitize input, XML boundaries, system prompt warning.

## Summary
- P1 (Critical): 1
- P2 (Important): 4
- P3 (Nice-to-have): 9
