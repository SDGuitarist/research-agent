# Pattern Recognition Specialist — Review Findings

**PR:** Background research agents: queue/digest skills + context system refactor
**Branch:** main (52e32bf..aae39bb)
**Date:** 2026-02-26
**Agent:** pattern-recognition-specialist

## Findings

### F1: Context Block Building Duplication
- **Severity:** P2
- **File:** research_agent/synthesize.py:167-175,456-464; research_agent/decompose.py:90-97; research_agent/skeptic.py:42-47
- **Issue:** The `<research_context>` XML block building pattern is duplicated in 4 places across 3 files. `skeptic.py` has a clean `_build_context_block()` helper, but other modules don't use it.
- **Suggestion:** Extract a shared helper into `sanitize.py` or a new `prompt_helpers.py` that all three files import. Single source of truth for the XML tag name.

### F3: Private Attribute Access from Public API
- **Severity:** P2
- **File:** research_agent/__init__.py:113-114
- **Issue:** `run_research_async()` accesses `agent._last_source_count` and `agent._last_gate_decision` — underscore-prefixed private attributes. Couples public API to internal implementation.
- **Suggestion:** Add public read-only properties to `ResearchAgent` (like existing `last_critique` property).

### F4: ResearchAgent Accumulates Mutable State Across Runs
- **Severity:** P2
- **File:** research_agent/agent.py:79-84,214-218
- **Issue:** Six mutable run-state attributes are reset manually at top of `_research_async()`. `_last_critique` is conspicuously missing from the reset block — it's set at line 179 but never cleared.
- **Suggestion:** Add `self._last_critique = None` to the reset block. Consider grouping run-specific state into a frozen `_RunState` dataclass.

### F5: Path Traversal Check Uses String Prefix Matching
- **Severity:** P2
- **File:** research_agent/context.py:54-58
- **Issue:** `str(path).startswith(str(contexts_resolved) + "/")` pattern for path containment has known edge cases. Defense layer 1 already blocks `/` and `..`, so this is defense-in-depth, but the standard Python idiom is safer.
- **Suggestion:** Use `path.is_relative_to(contexts_resolved)` (Python 3.9+). Tracked in `todos/054-pending-p1-path-traversal-resolve-context.md`.

### F2: Mixed Logging Style
- **Severity:** P3
- **File:** Multiple files in research_agent/
- **Issue:** f-strings vs `%s` formatting mixed in logging calls, even within the same file (context.py). Tracked in `todos/050-pending-p3-fstring-logging.md`.
- **Suggestion:** New code should prefer `%s` style. Auto-detect functions already follow this.

### F6: Auto-Detect Prompt Contains Unsanitized Context Name
- **Severity:** P3
- **File:** research_agent/context.py:168
- **Issue:** `available[0][0]` interpolated directly into prompt without sanitization. Low risk (filesystem-controlled) but inconsistent with project's sanitization discipline.
- **Suggestion:** Sanitize the example name. Tracked in `todos/057-pending-p2-unsanitized-auto-detect-prompt.md`.

### F7: Exception Handling Tuple Order Inconsistency
- **Severity:** P3
- **File:** research_agent/context.py:180; research_agent/decompose.py:158; research_agent/api_helpers.py:56
- **Issue:** Anthropic API exception tuples are caught in different orderings across files. No functional impact but inconsistent.
- **Suggestion:** Define `ANTHROPIC_API_ERRORS` tuple in `errors.py` and import everywhere.

### F8: synthesize_report Docstring Missing context Parameter
- **Severity:** P3
- **File:** research_agent/synthesize.py:89-120
- **Issue:** `context: str | None = None` parameter not documented in docstring Args section.
- **Suggestion:** Add `context: Optional business context for competitive positioning sections`.

### F9: Context Cache Uses Module-Level Mutable State
- **Severity:** P3
- **File:** research_agent/context.py:23-28
- **Issue:** `_context_cache` is module-level dict. Not thread-safe for concurrent async use. Works fine for CLI.
- **Suggestion:** Consider moving cache to `ResearchAgent` instance. Informational for now.

## Positive Findings

### F11: Additive Pattern Compliance
The PR follows the project's "additive pattern" well. Context changes layer on without changing downstream modules. `decompose.py` already accepted `context_content: str | None`, so auto-detect threads naturally.

### F12: Good Factory Method Usage
`ContextResult` uses well-implemented Factory Method pattern via classmethods with enforced invariants. Consistent with other frozen dataclasses in the codebase.

### F13: Naming Convention Consistency
All naming conventions (private `_prefix`, `UPPER_SNAKE` constants, `PascalCase` classes, `snake_case` functions) are followed consistently.

### F14: No Bare `except Exception`
All exception handlers catch specific types. Follows CLAUDE.md convention.

### F15: No TODO/FIXME/HACK Comments
Technical debt tracked in `todos/*.md` files, keeping code clean.

## Summary
- P1 (Critical): 0
- P2 (Important): 4
- P3 (Nice-to-have): 5
