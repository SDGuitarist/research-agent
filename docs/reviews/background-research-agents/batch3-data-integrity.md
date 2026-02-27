# Data Integrity Guardian — Review Findings

**PR:** Background research agents: queue/digest skills + context system refactor
**Branch:** feat/background-research-agents
**Date:** 2026-02-26
**Agent:** data-integrity-guardian

## Findings

### Non-Atomic File Writes in CLI Output Path
- **Severity:** P2
- **File:** research_agent/cli.py:350
- **Issue:** The CLI saves reports with `Path.write_text()`, which is not atomic. If the process crashes mid-write (keyboard interrupt during streaming, disk full), the report file is partially written. The codebase already has `safe_io.atomic_write()` for this purpose. Background agents writing via `-o` are particularly vulnerable — a partial file passes the queue skill's existence check and gets marked Completed with a corrupted report.
- **Suggestion:** Replace `output_path.write_text(report)` with `from research_agent.safe_io import atomic_write; atomic_write(output_path, report)`.

### Context Cache is Module-Level Global State
- **Severity:** P2
- **File:** research_agent/context.py:22-23
- **Issue:** `_context_cache` is a module-level dict shared across all `ResearchAgent` instances. `clear_context_cache()` is called at start of each run (agent.py:219), creating a cross-instance side effect. If two agents run concurrently via `run_research_async()`, one agent's cache clear invalidates the other's. Mitigated today since CLI runs one query at a time, and `_run_context` instance variable holds loaded context for the run.
- **Suggestion:** Future consideration: make cache instance-level rather than module-level if concurrent server use is planned.

### resolve_context_path Containment Check Uses String Prefix
- **Severity:** P3
- **File:** research_agent/context.py:54-58
- **Issue:** Containment check uses `str.startswith()` for path comparison. Can be fragile on case-insensitive filesystems (macOS HFS+/APFS). Python 3.9+ provides `Path.is_relative_to()` which handles edge cases. Practical risk is very low since Layer 1 character-level rejection blocks all realistic traversal before this layer.
- **Suggestion:** Replace `str.startswith` with `path.is_relative_to(contexts_resolved)` for consistency with the digest skill's own recommendation.

## Positive Patterns Noted

1. **Single-writer architecture** — main session is sole writer to queue.md and daily_spend.json; background agents only write reports via CLI
2. **Running state elimination** — removing `[~]` Running state prevents limbo items on crash
3. **Local variables for async safety** — `_research_async` uses local vars instead of mutating `self`
4. **Defense-in-depth path traversal** — two layers (character rejection + containment check) with thorough tests
5. **ContextResult frozen dataclass** — prevents accidental mutation of loaded context
6. **Context-conditional templates** — prevents hallucinated business sections in generic reports

## Summary
- P1 (Critical): 0
- P2 (Important): 2
- P3 (Nice-to-have): 1
