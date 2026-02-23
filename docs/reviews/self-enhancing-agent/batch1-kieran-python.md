# Kieran Python Reviewer — Review Findings

**PR:** Self-Enhancing Agent (self-critique feedback loop)
**Branch:** main (bad292e..57bf44e)
**Date:** 2026-02-23
**Agent:** kieran-python-reviewer

## Findings

### 1. Bare `except Exception` Disguised as Specific Handling
- **Severity:** P1
- **File:** research_agent/agent.py:155
- **Issue:** `except (CritiqueError, Exception) as e:` catches everything — `CritiqueError` in the tuple is redundant because `Exception` already covers it. Violates project convention: "Never bare `except Exception`".
- **Suggestion:** Catch only specific errors: `except (CritiqueError, APIError, RateLimitError, APIConnectionError, APITimeoutError, OSError) as e:`

### 2. Docstring Missing `critique_context` Parameter
- **Severity:** P1
- **File:** research_agent/decompose.py:106-123
- **Issue:** `decompose_query` signature includes `critique_context: str | None = None` but the docstring's `Args:` block does not document it. Developers reading the docstring won't know this parameter exists.
- **Suggestion:** Add the parameter to the docstring with a description of its purpose.

### 3. `CritiqueError` Declared but Never Raised
- **Severity:** P2
- **File:** research_agent/errors.py:48-50, research_agent/critique.py
- **Issue:** `CritiqueError` is defined and caught in `agent.py` but nothing ever raises it. `evaluate_report` catches API errors internally and returns defaults. `save_critique` delegates to `atomic_write` which raises `StateError`. Dead code creating false sense of structured error handling.
- **Suggestion:** Either have critique functions raise `CritiqueError` for domain-specific failures, or remove it until actually needed.

### 4. `_summarize_patterns` Filtering Logic Split Confusingly
- **Severity:** P2
- **File:** research_agent/context.py:176-225
- **Issue:** `load_critique_history` passes all valid critiques to `_summarize_patterns`, which internally filters to only passing ones. Docstring says "fewer than 3 valid critiques" but actually means "fewer than 3 valid **passing** critiques."
- **Suggestion:** Fix the docstring or pre-filter in `load_critique_history` before checking threshold.

### 5. Hardcoded `Path("reports/meta")` in Agent
- **Severity:** P2
- **File:** research_agent/agent.py:149, :193
- **Issue:** Meta directory hardcoded as relative path in two places. Not configurable, depends on CWD at runtime. Other configurable paths (e.g. `schema_path`) go through the constructor.
- **Suggestion:** Add `meta_dir` parameter to `__init__` or define a module-level constant `DEFAULT_META_DIR`.

### 6. Duplicate Score Tuple in `CritiqueResult`
- **Severity:** P2
- **File:** research_agent/critique.py:58-74
- **Issue:** Both `overall_pass` and `mean_score` properties independently construct the same `scores` tuple. DRY violation — adding a dimension requires updating both.
- **Suggestion:** Extract a private `_scores` property that both computed properties use.

### 7. `getattr` with Default 0 Hides Attribute Errors
- **Severity:** P2
- **File:** research_agent/critique.py:144-149
- **Issue:** `getattr(f, "critical_count", 0)` on untyped list elements silently masks bugs if wrong type is passed.
- **Suggestion:** Type the parameter as `list[SkepticFinding] | None` and use direct attribute access.

### 8. Test Reimplements Agent Logic Instead of Calling It
- **Severity:** P2
- **File:** tests/test_critique.py:232-269
- **Issue:** `test_critique_history_loaded_at_start` manually does `agent._critique_context = critique_ctx.content` instead of calling `_research_async`. Tests Python assignment, not agent behavior. Gives false confidence.
- **Suggestion:** Either test the actual async method with mocks, or extract critique loading into a testable helper.

### 9. f-string in Logger Calls
- **Severity:** P3
- **File:** research_agent/agent.py:156, research_agent/context.py:265-269
- **Issue:** Logger calls use f-strings instead of lazy `%s` formatting. Wastes string interpolation when log level is disabled.
- **Suggestion:** Use `logger.warning("Self-critique failed: %s", e)`.

### 10. `save_critique` Does Not Validate `meta_dir` is a Directory
- **Severity:** P3
- **File:** research_agent/critique.py:237-271
- **Issue:** If `meta_dir` points to a file, it raises an obscure `OSError` rather than a clear error.
- **Suggestion:** Minor — a pre-check `if meta_dir.exists() and not meta_dir.is_dir()` would give clearer errors.

### 11. `_validate_critique_yaml` Does Not Validate `mean_score` or `timestamp`
- **Severity:** P3
- **File:** research_agent/context.py:146-173
- **Issue:** Validation checks dimension scores and text fields but not `mean_score` (should be float) or `timestamp` (should be int). Malformed values would pass.
- **Suggestion:** Low priority — fields not consumed downstream. Add validation if schema expands.

### 12. `_parse_critique_response` First-Line Truncation Has Redundant Code
- **Severity:** P3
- **File:** research_agent/critique.py:103-111
- **Issue:** `.split("\n")[0]` is redundant since the regex `.+` already captures only one line (`.` doesn't match `\n`).
- **Suggestion:** Remove `.split("\n")[0]` or document that multi-line responses are intentionally truncated.

### 13. Inconsistent `@pytest.mark.asyncio` Usage
- **Severity:** P3
- **File:** tests/test_relevance.py:1001-1032
- **Issue:** `TestScoringAdjustmentsParam` uses explicit `@pytest.mark.asyncio` while other async tests in the same file don't (project uses auto mode).
- **Suggestion:** Remove explicit marks for consistency with rest of file.

### 14. Unused `AsyncMock` Import
- **Severity:** P3
- **File:** tests/test_critique.py:6
- **Issue:** `AsyncMock` is imported but never used — all mocks use `MagicMock` since `evaluate_report` is synchronous.
- **Suggestion:** Remove unused import.

### 15. Bare `Counter` Type Annotation
- **Severity:** P3
- **File:** research_agent/context.py:202
- **Issue:** `weakness_counter: Counter = Counter()` should be `Counter[str]` since the annotation is already there.
- **Suggestion:** `weakness_counter: Counter[str] = Counter()`

## Summary
- P1 (Critical): 2
- P2 (Important): 6
- P3 (Nice-to-have): 7
