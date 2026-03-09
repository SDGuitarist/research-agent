# HANDOFF — Research Agent

**Date:** 2026-03-08
**Branch:** `main`
**Phase:** Work COMPLETE — next step is Review (Cycle 25)

## What Was Done

Cycle 25 work phase (corrected scope per Codex plan review findings):

- Added `parse_context_file()` public wrapper in `research_agent/context.py`
- Updated `research_agent/cli.py` to import `parse_context_file` instead of `_parse_template`
- Updated `tests/test_context.py`: replaced 1 import, 1 docstring, 22 call sites (zero `_parse_template` references remain)
- **Not changed:** `__init__.py`, `__all__`, `mcp_server.py`, `test_public_api.py`, no new scripts
- MCP parity lint script deferred — existing `test_mcp_server.py::test_all_tools_mentioned_in_instructions` serves as the fast check

Commits:
- `881bfd4` feat(25): add parse_context_file public wrapper and update imports
- `61936bb` docs(25): add compound artifacts for cycle 25 housekeeping

938 tests passing.

## Key Artifacts

| Phase | Location |
|-------|----------|
| Brainstorm | `docs/brainstorms/2026-03-08-cycle-25-housekeeping-brainstorm.md` |
| Plan | `docs/plans/2026-03-08-cycle-25-housekeeping-plan.md` |
| Plan review | `docs/reviews/2026-03-08-cycle-25-codex-plan-findings.md` |
| Work | commits `881bfd4`, `61936bb` on `main` |

## Next Step

Start the review phase. Send to Codex:

```
You are reviewing cycle 25 of the research-agent project. This is a small housekeeping cycle that added a public wrapper function.

Review scope (2 commits on main):
- 881bfd4 feat(25): add parse_context_file public wrapper and update imports
- 61936bb docs(25): add compound artifacts for cycle 25 housekeeping

Files changed:
- research_agent/context.py (added parse_context_file wrapper)
- research_agent/cli.py (import swap: _parse_template → parse_context_file)
- tests/test_context.py (import swap + 22 call site renames)

Review checklist:
1. Does parse_context_file() correctly delegate to _parse_template()?
2. Are there any remaining _parse_template references in cli.py or test_context.py?
3. Is __init__.py unchanged (parse_context_file intentionally NOT exported)?
4. Are there any test_public_api.py implications?
5. Any regressions or missed call sites?

Run: git diff 5f31b3b..HEAD to see all changes.
Run: grep -r "_parse_template" research_agent/cli.py tests/test_context.py to verify no stale references.

Write findings to docs/reviews/2026-03-08-cycle-25-code-review-findings.md.
```

## Deferred Items

- **MCP parity lint script** — deferred; existing pytest test is sufficient
- **Tier 3 model routing** (summarization) — deferred indefinitely
- **IDN/punycode domain matching** — known limitation, acceptable

## Three Questions

1. **Hardest implementation decision?** Whether to use `replace_all` for the 22 `_parse_template(` call sites or do them individually. Used `replace_all` — all calls have identical signature, no risk of false matches.
2. **What was considered but left alone?** Exporting `parse_context_file` from `__init__.py`. The Codex plan review correctly flagged this as unnecessary — it's used by CLI (internal) and tests, not external consumers.
3. **Least confident about going into review?** Whether the test class names (`TestParseTemplate`, `TestParseTemplateFrontmatterDetection`) should also be renamed to match the public wrapper. Left them as-is since class names don't create import coupling.
