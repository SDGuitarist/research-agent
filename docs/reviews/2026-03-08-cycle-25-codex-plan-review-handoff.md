# Codex Plan Review Handoff — Cycle 25: Housekeeping (MCP Parity Lint + parse_context_file)

## Your Job

Review the **plan** for correctness and completeness before work begins. This is a plan review, not a code review — no code has been written yet.

## Read First

1. `CLAUDE.md` — repo conventions, architecture, test commands
2. `docs/plans/2026-03-08-cycle-25-housekeeping-plan.md` — the plan to review
3. `docs/brainstorms/2026-03-08-cycle-25-housekeeping-brainstorm.md` — brainstorm context
4. `docs/reviews/CODEX-REVIEW-GATE.md` — review priorities for this repo

## What the Plan Proposes

Two independent items in a single work session (~60 lines total):

### Item 1: `parse_context_file()` public wrapper

- Add thin public function in `context.py` that delegates to `_parse_template()`
- Export from `__init__.py`
- Swap imports in `cli.py` (1 site) and `test_context.py` (22 call sites + 1 import)
- No behavior change — pure naming/coupling fix

### Item 2: MCP parity lint script

- New `scripts/lint_mcp_parity.py`
- Uses `asyncio.run(mcp.list_tools())` to get registered tool names
- Compares against `mcp.instructions` string
- Exits 0 (all tools mentioned) or 1 (missing tools)

## Files That Will Change

| File | Change |
|------|--------|
| `research_agent/context.py` | Add `parse_context_file()` after `_parse_template()` |
| `research_agent/__init__.py` | Add import + `__all__` entry |
| `research_agent/cli.py` | Swap `_parse_template` → `parse_context_file` (2 lines) |
| `tests/test_context.py` | Swap import + 22 call sites + 1 docstring |
| `scripts/lint_mcp_parity.py` | New file |

## Files That Must NOT Change

- `research_agent/mcp_server.py` — no MCP behavior changes
- `research_agent/agent.py` — no pipeline changes
- `research_agent/context.py:_parse_template()` — function body stays identical
- `research_agent/context.py:load_full_context()` — keeps calling `_parse_template` directly

## Risks to Scrutinize

1. **Import completeness** — The plan says 22 `_parse_template` call sites in `test_context.py`. Verify this count against the actual file. A missed site means tests fail.

2. **`__init__.py` export** — The plan adds `parse_context_file` to exports. Is this correct? Other context functions (`list_available_contexts`, `resolve_context_path`, `load_critique_history`) are already exported. But `_parse_template` was deliberately private. Should the public wrapper follow the same export pattern, or is it an internal-only convenience?

3. **Lint script `asyncio.run()` safety** — The script calls `asyncio.run(mcp.list_tools())`. This works standalone, but would fail if called from within an existing event loop. Is this a concern for any foreseeable use case (e.g., running from a Jupyter notebook or async test runner)?

4. **Lint script vs. existing pytest test** — `tests/test_mcp_server.py:test_all_tools_mentioned_in_instructions` already checks the same thing. Is the lint script adding enough value to justify a second implementation? Or should the plan just document how to run the focused pytest test instead?

5. **`_parse_template` still importable from tests** — After swapping to `parse_context_file`, `_parse_template` is still importable. If a future developer adds a test importing `_parse_template` directly, we're back to the coupling problem. Should there be a test or lint to prevent private imports in test files?

## Plan Quality Gate Check

Verify the plan answers these four questions adequately:

1. **What exactly is changing?** — ✅ Listed in Steps 1-5
2. **What must not change?** — ✅ Stated per step
3. **How will we know it worked?** — ✅ 938 tests pass + lint script exits 0
4. **Most likely way this plan is wrong?** — Stated as "missed import site." Verify if there are other failure modes.

## What to Produce

Write findings to `docs/reviews/2026-03-08-cycle-25-codex-plan-findings.md` with:

- Priority (P1/P2/P3) per CODEX-REVIEW-GATE priority order
- Whether each finding is a **blocker** (must fix before work) or **advisory** (note for work phase)
- Specific line numbers or file references where relevant
- If any risks above are confirmed, note the exact impact

Focus on: Is the plan **correct enough** that a developer can execute it mechanically without making design decisions? Flag anything ambiguous, incorrect, or missing.
