# Agent-Native Reviewer — Review Findings

**PR:** Background research agents: queue/digest skills + context system refactor
**Branch:** feat/background-research-agents
**Date:** 2026-02-26
**Agent:** agent-native-reviewer

## Findings

### --list Reports Has No Programmatic Equivalent
- **Severity:** P2
- **File:** research_agent/cli.py:85-123
- **Issue:** An agent using the Python API cannot discover what reports already exist. `list_reports()` prints to stdout and returns `None` — not reusable programmatically. Agents must shell out or manually glob `reports/`.
- **Suggestion:** Add `list_reports() -> list[ReportInfo]` to `__init__.py` returning structured data (date, query_name, path).

### --critique Has No Programmatic Equivalent
- **Severity:** P2
- **File:** research_agent/cli.py:264-281
- **Issue:** `critique_report_file()` exists in `research_agent/critique.py:221` but is not exported in `__init__.py`. Agents cannot programmatically critique reports without importing internal modules.
- **Suggestion:** Export `critique_report_file` and `CritiqueResult` in `__init__.py.__all__`.

### --no-critique and --max-sources Not Exposed in Public API
- **Severity:** P2
- **File:** research_agent/__init__.py:28-57
- **Issue:** CLI users can skip critique (`--no-critique`) and override source count (`--max-sources`), but `run_research()` does not accept these parameters. The `ResearchAgent` constructor supports both, but the public API function doesn't pass them through.
- **Suggestion:** Add `skip_critique: bool = False` and `max_sources: int | None = None` parameters to `run_research()` and `run_research_async()`.

### CLI --context Does Not Catch ValueError for Path Traversal
- **Severity:** P2
- **File:** research_agent/cli.py:313
- **Issue:** The CLI catches `FileNotFoundError` from `resolve_context_path()` but not `ValueError` (raised for path traversal attempts like `--context ../etc/passwd`). An uncaught `ValueError` produces a Python traceback instead of a clean error message.
- **Suggestion:** Change `except FileNotFoundError` to `except (FileNotFoundError, ValueError)`.

### Research Log Append is CLI-Only
- **Severity:** P3
- **File:** research_agent/cli.py:48-67
- **Issue:** The CLI appends to `research_log.md` on every run. API callers do not get this behavior, so CLI and API runs diverge in tracking over time.
- **Suggestion:** Move `append_research_log()` into the agent or expose in public API as opt-in: `run_research(..., log=True)`.

### --critique-history Has No Programmatic Equivalent
- **Severity:** P3
- **File:** research_agent/cli.py:255-261
- **Issue:** `load_critique_history()` exists but is not exported. Agents wanting performance trend data cannot easily access it.
- **Suggestion:** Export `load_critique_history` in `__init__.py.__all__`.

## Positive Patterns Noted

1. **Context system is agent-native by design** — `list_available_contexts()`, `resolve_context_path()`, and auto-detect all exported and usable programmatically
2. **Public API context parameter achieves parity** — `run_research(context="pfe")` mirrors `--context pfe` exactly
3. **Queue file as shared workspace** — readable/writable by both humans and agents with documented format
4. **Security hardening protects API callers** — `resolve_context_path()` defense-in-depth works for both CLI and API
5. **Sub-agent delegation in digest** — reading reports via Task sub-agents respects calling agent's context budget

## Agent-Native Score

- 12/18 capabilities are agent-accessible (via Python API or shared files)
- 6 gaps identified (4 pre-existing, not introduced by this PR)
- The context system changes are exemplary agent-native design
- Pre-existing CLI gaps are more visible now that this PR raised the bar

## Summary
- P1 (Critical): 0
- P2 (Important): 4
- P3 (Nice-to-have): 2
