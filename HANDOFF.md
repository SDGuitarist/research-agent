# HANDOFF — Research Agent

**Date:** 2026-04-05
**Branch:** `main`
**Phase:** Cycle 27 — Work, Session 1 COMPLETE. Ready for Session 2.

## Current State

Session 1 (idempotent sanitization) implemented and committed. `sanitize_content()` now uses `html.unescape()` normalization before escaping. 920 tests pass (test_mcp_server skipped — pre-existing fastmcp install issue). One test updated: `test_ampersand_before_angle_brackets` → `test_already_escaped_input_is_idempotent`. 13 new idempotency invariant tests added.

## Key Artifacts

| Phase | Location |
|-------|----------|
| Brainstorm | `docs/brainstorms/2026-04-05-cycle-27-input-validation-brainstorm.md` |
| Plan | `docs/plans/2026-04-05-cycle-27-input-validation-plan.md` |
| Session 1 commit | `fix(27-1): make sanitize_content idempotent via unescape-then-escape` |

## Deferred Items

- **Tier 3 model routing** (summarization) — deferred indefinitely
- **IDN/punycode domain matching** — known limitation, acceptable
- **MCP `--cost` + `--critique-history` tools** (#123) — Cycle 31

## Three Questions

1. **Hardest implementation decision?** Whether the updated test should assert the new idempotent behavior (`"&lt;script&gt;"`) or be replaced entirely. Chose to rename and update — the test now verifies the correct idempotent behavior instead of the old corruption behavior.
2. **What did you consider changing but left alone?** Considered adding a `NUL` byte stripping step to `sanitize_content()` for extra defense. Left it out — not in the plan, no evidence of NUL bytes in web content causing issues.
3. **Least confident about going into review?** The `html.unescape()` call converts ALL HTML entities, not just the three we care about (`&amp;`, `&lt;`, `&gt;`). If any downstream code relies on HTML entities like `&nbsp;` surviving sanitization, this could change behavior. The full test suite passes, so no known breakage.

### Prompt for Next Session

```
Read docs/plans/2026-04-05-cycle-27-input-validation-plan.md. Implement Session 2: Vague Query Detection. Relevant files: research_agent/query_validation.py, research_agent/errors.py, research_agent/agent.py, tests/test_query_validation.py, tests/test_agent.py. Do only Session 2 — commit and stop.
```
