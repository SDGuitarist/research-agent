# Kieran Python Reviewer — Review Findings

**PR:** Background research agents: queue/digest skills + context system refactor
**Branch:** main (52e32bf..aae39bb)
**Date:** 2026-02-26
**Agent:** kieran-python-reviewer

## Findings

### P1-1: ValueError from resolve_context_path uncaught in CLI
- **Severity:** P1
- **File:** research_agent/cli.py:311-318
- **Issue:** `resolve_context_path()` raises `ValueError` for path traversal attempts (names containing `/`, `\`, or starting with `.`), but the CLI only catches `FileNotFoundError`. A user typing `--context ../evil` gets an unhandled `ValueError` traceback.
- **Suggestion:** Add `ValueError` to the except clause alongside `FileNotFoundError`:
```python
try:
    context_path = resolve_context_path(args.context)
except (FileNotFoundError, ValueError) as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
```

### P1-2: ValueError from resolve_context_path uncaught in public API
- **Severity:** P1
- **File:** research_agent/__init__.py:99-102
- **Issue:** Same problem in `run_research_async()`. The `resolve_context_path(context)` call can raise `ValueError`, but nothing catches it. Should convert to `ResearchError` for consistency.
- **Suggestion:**
```python
try:
    context_path = resolve_context_path(context)
except (FileNotFoundError, ValueError) as e:
    raise ResearchError(str(e)) from e
```

### P1-3: Path traversal defense via string prefix check is fragile
- **Severity:** P1
- **File:** research_agent/context.py:56
- **Issue:** Defense layer 2 uses `str(path).startswith(str(contexts_resolved) + "/")`, a string prefix check on resolved paths. This can fail on edge cases like symlinks or path prefixes (`/tmp/contexts` vs `/tmp/contexts-other`). Python provides a safer alternative.
- **Suggestion:** Use `Path.is_relative_to()` (Python 3.9+):
```python
if not path.is_relative_to(contexts_resolved):
    raise ValueError(...)
```

### P2-1: Public API accesses private attributes
- **Severity:** P2
- **File:** research_agent/__init__.py:113-114
- **Issue:** `run_research_async()` reads `agent._last_source_count` and `agent._last_gate_decision` — both underscore-prefixed private attributes. Couples public API to internal implementation.
- **Suggestion:** Add public read-only properties to `ResearchAgent` (like existing `last_critique` property).

### P2-2: _load_context_for wrapper adds no value
- **Severity:** P2
- **File:** research_agent/agent.py:91-100
- **Issue:** Thin wrapper method called exactly once. The conditional logic is trivial enough to inline.
- **Suggestion:** Inline at the call site and delete the method.

### P2-3: Module-level mutable cache with no thread-safety
- **Severity:** P2
- **File:** research_agent/context.py:23
- **Issue:** `_context_cache` is a module-level mutable dict. While CLI is single-threaded, the public API is designed for async contexts. Two coroutines could interfere.
- **Suggestion:** Document as not thread-safe. Consider making cache an instance attribute on `ResearchAgent`.

### P2-4: Auto-detect prompt contains unsanitized context filename
- **Severity:** P2
- **File:** research_agent/context.py:154-169
- **Issue:** `available[0][0]` (context file name from filesystem) is interpolated raw into the LLM prompt as an example. Breaks the otherwise consistent sanitization discipline.
- **Suggestion:** Sanitize the example name: `sanitize_content(available[0][0])`.

### P2-5: synthesize_draft/synthesize_final implicit section numbering coupling
- **Severity:** P2
- **File:** research_agent/synthesize.py:291-325
- **Issue:** `synthesize_draft` and `synthesize_final` branch independently on context/skeptic to produce sections with implicit numbering contracts. If one changes without the other, report structure breaks silently.
- **Suggestion:** Add a comment block mapping the section plan, or extract section numbering as shared configuration.

### P2-6: auto_detect_context "none" parsing too permissive
- **Severity:** P2
- **File:** research_agent/context.py:186
- **Issue:** Checks `answer in ("none", "\"none\"")` before stripping quotes. Could miss `'none'` or other variants. Currently works by accident (falls through to "unrecognized" warning).
- **Suggestion:** Check `cleaned` after stripping first:
```python
cleaned = answer.strip("\"'")
if cleaned == "none":
    return None
```

### P3-1: Skill file Task sub-agent syntax not explicit
- **Severity:** P3
- **File:** .claude/skills/research-digest/SKILL.md:56
- **Issue:** References "Task sub-agent" without concrete tool invocation syntax example.
- **Suggestion:** Minor — skill files are consumed by Claude Code, not humans.

### P3-2: _PREVIEW_LINES constant used only once
- **Severity:** P3
- **File:** research_agent/context.py:106
- **Issue:** Module-level constant used only in `list_available_contexts()`.
- **Suggestion:** Acceptable as-is. Inline would also be fine.

### P3-3: f-string used for logger calls (inconsistent)
- **Severity:** P3
- **File:** research_agent/context.py:330,334; research_agent/agent.py:349,665,823
- **Issue:** Mixed f-string and `%s` logging styles. Already tracked in `todos/050-pending-p3-fstring-logging.md`.
- **Suggestion:** Use `%s` style for all new logger calls.

### P3-4: ContextResult classmethods use quoted string return type
- **Severity:** P3
- **File:** research_agent/context_result.py:39,50,55,60
- **Issue:** Uses `"ContextResult"` forward reference instead of `Self` from `typing` (Python 3.14 supports it).
- **Suggestion:** Use `from typing import Self` and annotate `-> Self`.

### P3-5: Skill file hardcodes absolute path
- **Severity:** P3
- **File:** .claude/skills/research-queue/SKILL.md:174
- **Issue:** Hardcodes `/Users/alejandroguillen/Projects/research-agent` — non-portable.
- **Suggestion:** Use `pwd` or a placeholder.

### P3-6: Test helper _mock_client does not use self
- **Severity:** P3
- **File:** tests/test_context.py:272-279
- **Issue:** Instance method that never uses `self`. Should be `@staticmethod`.
- **Suggestion:** Decorate with `@staticmethod`.

### P3-7: _make_critique test helper untyped
- **Severity:** P3
- **File:** tests/test_context.py:390
- **Issue:** No type hints on test helper. Tests are exempt per project conventions.
- **Suggestion:** No action needed.

## Summary
- P1 (Critical): 3
- P2 (Important): 6
- P3 (Nice-to-have): 7
