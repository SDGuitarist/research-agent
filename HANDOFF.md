# HANDOFF — Research Agent

**Date:** 2026-04-23
**Branch:** `feat/31-novelty-decomposition-mcp-critique`
**Phase:** Cycle 31 WORK COMPLETE. Ready for review.

## What Was Done

### Session 1: Novelty-biased decomposition (commit `8bffaef`)
- `novelty_queries: int` field on `ResearchMode` (quick=0, standard=1, deep=2)
- `__post_init__` validation: 0-3 range with `MAX_SUB_QUERIES` comment
- `NOVELTY_INSTRUCTION_TEMPLATE` module-level constant in `decompose.py`
- Per-sub-query overlap requirement in prompt wording
- System prompt built as variable, novelty appended after last rule bullet
- Threaded from `agent.py` → `decompose_query()`
- `ModeInfo` + `list_modes()` + `list_research_modes()` all expose the field
- 17 new tests

### Session 2: MCP `get_critique_history` tool (commit `56f44d4`)
- `@mcp.tool get_critique_history()` with `except Exception` boundary catch-all
- Docstring specifies 3 passing critiques (`overall_pass: true`) threshold
- No-history message explains the passing threshold
- Instructions string updated, MCP lint passes 8/8
- 4 new tests

### Docs (commit `a66ccbb`)
- Brainstorm, plan, and Codex review handoff

**Files changed:** modes.py, results.py, __init__.py, decompose.py, agent.py, mcp_server.py, test_modes.py, test_decompose.py, test_mcp_server.py, test_results.py
**Tests:** 1116 passing (was 1095)

## Key Artifacts

| Phase | Location |
|-------|----------|
| Brainstorm | `docs/brainstorms/2026-04-22-cycle-31-novelty-decomposition-mcp-tools-brainstorm.md` |
| Plan | `docs/plans/2026-04-23-feat-novelty-decomposition-mcp-cost-critique-plan.md` |
| Codex Handoff | `docs/plans/2026-04-23-codex-plan-review-handoff.md` |

## Deferred Items

- **ANTHROPIC_ERRORS consumption at 10+ call sites** — mechanical replacement for micro-cycle
- **`show_costs` MCP tool** — intentionally dropped (covered by `list_research_modes`)
- **A/B live validation of novelty decomposition** — run when API keys renewed
- **Diversity gate threshold tuning** — monitor short_report frequency for niche topics after API key renewal
- **`META_DIR` promotion to public location** — accepted as existing pattern (cli.py does same)
- **`to_mode_info()` method on ResearchMode** — eliminates manual ModeInfo field syncing

## Three Questions

1. **Hardest implementation decision?** Building the system prompt as a variable instead of inline string literal. The existing code had a single string in the `system=` kwarg — refactoring to `system_prompt = ...` + conditional append was the cleanest approach but touched the most lines.
2. **What did you consider changing but left alone?** The existing prompt rule "Keep the original query's key terms in at least one sub-query" — it's technically weaker than the per-sub-query validation requires, but changing the original rule would be scope creep. The novelty template adds its own explicit per-sub-query retention requirement.
3. **Least confident going into review?** Whether the `get_critique_history` `except Exception` catch-all is too broad — `load_critique_history` has its own internal error handling and the function docstring says it never raises, but the boundary pattern requires the catch-all for defense-in-depth.

## Prompt for Next Session

```
Read HANDOFF.md for context. This is research-agent on branch
feat/31-novelty-decomposition-mcp-critique.
Cycle 31 work complete. Run /workflows:review on this branch.
Plan: docs/plans/2026-04-23-feat-novelty-decomposition-mcp-cost-critique-plan.md
```
