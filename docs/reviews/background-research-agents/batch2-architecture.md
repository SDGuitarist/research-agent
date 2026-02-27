# Architecture Strategist — Review Findings

**PR:** Background research agents: queue/digest skills + context system refactor
**Branch:** main (52e32bf..aae39bb)
**Date:** 2026-02-26
**Agent:** architecture-strategist

## Findings

### Module-level mutable state in context cache
- **Severity:** P2
- **File:** research_agent/context.py:23
- **Issue:** `_context_cache` is module-level mutable state. Works for single-threaded CLI, but if two `ResearchAgent` instances run concurrently (e.g., in an async server), they share and mutate the same cache. One agent's `clear_context_cache()` would invalidate the other's cached lookups. Currently safe because queue skill launches separate processes.
- **Suggestion:** Move cache to `ResearchAgent` instance, or document explicitly that concurrent in-process use is not supported.

### `load_full_context` FAILED status silently drops to no-context
- **Severity:** P2
- **File:** research_agent/context.py:98-100
- **Issue:** When an `OSError` occurs reading a context file, `load_full_context()` returns `ContextResult.failed()`. The `__bool__` method returns `False` for FAILED, so it's treated identically to NOT_CONFIGURED. A context file that exists but is unreadable (permissions error) is silently treated as "no context" with no user-visible warning.
- **Suggestion:** In `_load_context_for()` at agent.py:91, check if result status is FAILED and log a user-visible warning with the error message.

### Skill file hardcodes absolute path to project directory
- **Severity:** P2
- **File:** .claude/skills/research-queue/SKILL.md:174
- **Issue:** Queue skill contains hardcoded `/Users/alejandroguillen/Projects/research-agent`. Non-portable and leaks personal info.
- **Suggestion:** Replace with reference to current working directory or `{project_root}` placeholder.

### _run_context stored on self inconsistent with local-variable pattern
- **Severity:** P3
- **File:** research_agent/agent.py:81
- **Issue:** `self._run_context` is per-run state stored on the instance. The local-variable pattern was applied for `effective_context_path` and `effective_no_context` (fixing todo 056), but `_run_context` itself still uses `self`. It is overwritten at the start of each run, so it works correctly.
- **Suggestion:** Accept as-is. Threading it as a local through the deep call chain would add complexity for minimal benefit.

### Deep mode synthesis_instructions still references <research_context>
- **Severity:** P3
- **File:** research_agent/modes.py:154-157
- **Issue:** Leftover from pre-refactor design. The instructions tell the LLM to "Reference <research_context> if provided" but this path uses the draft/final synthesis, not `synthesize_report()`. Harmless but redundant.
- **Suggestion:** Clean up when convenient. Low priority.

### Public API raises FileNotFoundError instead of ResearchError
- **Severity:** P3
- **File:** research_agent/__init__.py:100
- **Issue:** `resolve_context_path()` raises `FileNotFoundError` which propagates to callers as an unhandled error instead of the expected `ResearchError`. Inconsistent with the rest of the validation in `run_research_async()`.
- **Suggestion:** Wrap in try/except converting to `ResearchError`.

### Queue skill lacks idempotency for interrupted runs
- **Severity:** P3
- **File:** .claude/skills/research-queue/SKILL.md:248
- **Issue:** If session dies after agent launch but before completion is processed, re-running launches the same query again (duplicate spend). Budget tracking prevents overspend, and duplicate reports are harmless.
- **Suggestion:** Accept as-is — documented tradeoff. Could check `reports/` for matching files before re-launching in future.

### CLAUDE.md says "three-way" for a four-state ContextResult
- **Severity:** P3
- **File:** CLAUDE.md (architecture section) vs research_agent/context_result.py
- **Issue:** CLAUDE.md says "Three-way context result (loaded/empty/not_configured)" but there are four states (LOADED, NOT_CONFIGURED, EMPTY, FAILED).
- **Suggestion:** Update CLAUDE.md to say "Four-way context result."

## Summary
- P1 (Critical): 0
- P2 (Important): 3
- P3 (Nice-to-have): 5
