# Code Simplicity Reviewer — Review Findings

**PR:** Background research agents: queue/digest skills + context system refactor
**Branch:** main (52e32bf..aae39bb)
**Date:** 2026-02-26
**Agent:** code-simplicity-reviewer

## Findings

### F3: Auto-detect fallback silently kills legacy default context
- **Severity:** P2
- **File:** research_agent/agent.py:233-236
- **Issue:** When `auto_detect_context` returns `None`, the code sets `effective_no_context = True` with source `"--context none"`. This is misleading — the user didn't pass `--context none`, auto-detect just found no match. It also prevents `load_full_context()` from falling back to the default `research_context.md` file. If a user has both the legacy default and a `contexts/` directory, auto-detect silently kills the legacy fallback.
- **Suggestion:** If `contexts/` directory replaces the old default, document that explicitly. Fix the misleading source string to `"auto-detect: no match"`.

### F4: Four-way section_list branching in synthesize_final
- **Severity:** P2
- **File:** research_agent/synthesize.py:509-540
- **Issue:** Section list branches on two booleans (`context` and `skeptic_findings`), creating 4 nearly-identical string blocks (32 lines). Only differences: which sections are included and numbering.
- **Suggestion:** Build section list incrementally:
```python
sections = []
next_num = 5 if not context else 9
if context:
    sections.append(f"{next_num}. **Competitive Implications**...")
    next_num += 1
    sections.append(f"{next_num}. **Positioning Advice**...")
    next_num += 1
if skeptic_findings:
    sections.append(f"{next_num}. **Adversarial Analysis**...")
    next_num += 1
sections.append(f"{next_num}. **Limitations & Gaps**...")
section_list = "\n".join(sections)
```

### F6: Module-level _context_cache survives across test runs
- **Severity:** P2
- **File:** research_agent/context.py:23
- **Issue:** Module-level dict persists across test cases unless explicitly cleared. Tests use `tmp_path` with unique paths so it works in practice, but if a test uses the same path string, cache pollution could cause flaky tests.
- **Suggestion:** Consider moving cache to `ResearchAgent` instance.

### F10: Two overlapping constructor parameters for context control
- **Severity:** P2
- **File:** research_agent/agent.py:66-67
- **Issue:** `context_path: Path | None` and `no_context: bool` interact non-obviously. If both are passed, `no_context` wins. This contradictory call should probably be an error. Leaks CLI concerns into the agent API.
- **Suggestion:** Consider a single `context` parameter: `context: Path | None | Literal["none"] = None`. This is a public API change, so defer to next minor version.

### F11: run_research_async context resolution duplicates CLI logic
- **Severity:** P2
- **File:** research_agent/__init__.py:96-106
- **Issue:** Same 6-line `resolve_context_path` -> check None -> set `no_context` pattern repeated in both `__init__.py` and `cli.py`.
- **Suggestion:** Extract shared helper `resolve_context_args(context_name) -> tuple[Path | None, bool]`.

### F1: _load_context_for is a trivial wrapper
- **Severity:** P3
- **File:** research_agent/agent.py:91-100
- **Issue:** 2-line method called once. Adds cognitive load without benefit.
- **Suggestion:** Inline at call site and delete the method.

### F2: Dual path traversal defense layers are redundant
- **Severity:** P3
- **File:** research_agent/context.py:47-59
- **Issue:** If defense layer 1 rejects all slashes and dots, defense layer 2 can never trigger. Defense-in-depth is fine for security code, but comments overstate the independence of the layers.
- **Suggestion:** Keep both layers but simplify comments. Informational only.

### F5: list_available_contexts reads full file for 5-line preview
- **Severity:** P3
- **File:** research_agent/context.py:120-128
- **Issue:** Reads entire file then takes first 5 lines. Context files are small, so this is trivial waste.
- **Suggestion:** Informational only — not worth changing.

### F7: auto_detect_context uses sync client wrapped in asyncio.to_thread
- **Severity:** P3
- **File:** research_agent/agent.py:227-229; research_agent/context.py:131-199
- **Issue:** Uses synchronous `Anthropic` client, agent wraps in `asyncio.to_thread()`. Agent already has `self.async_client`. Could use async client directly.
- **Suggestion:** Low priority — works correctly. Consider on future refactor.

### F12: synthesize_draft has two large duplicated string literals
- **Severity:** P3
- **File:** research_agent/synthesize.py:291-325
- **Issue:** `has_context` and `else` branches share structure (preamble, closing rules, BALANCE_INSTRUCTION) with only section lists differing.
- **Suggestion:** Extract section lists as data, build instruction string once.

### F13: Test patches may miss CONTEXTS_DIR mock
- **Severity:** P2
- **File:** tests/test_agent.py:260 and similar
- **Issue:** Standard/deep mode tests patch `load_full_context` but don't patch `CONTEXTS_DIR.is_dir`, so they depend on the real filesystem. Since `contexts/pfe.md` exists in the repo, these tests could trigger real auto-detect API calls.
- **Suggestion:** Add `patch("research_agent.agent.CONTEXTS_DIR")` with `mock_ctx_dir.is_dir.return_value = False` to all non-auto-detect test fixtures.

## Summary
- P1 (Critical): 0
- P2 (Important): 6
- P3 (Nice-to-have): 5
