# Review Context — Research Agent

## Risk Chain

**Brainstorm risk:** Whether the novelty prompt instruction will produce meaningfully different sub-queries without being so vague that it degrades decomposition quality.

**Plan mitigation:** Drafted concrete prompt instruction framing novelty in search-query terms ("angles that typical searches would miss"), validated via three trace-throughs across query types against `_validate_sub_queries()`.

**Work risk (from Feed-Forward):** Whether the `get_critique_history` `except Exception` catch-all is too broad — validated as consistent with established MCP boundary pattern by all 7 review agents.

**Review resolution:** 0 P1, 4 P2, 2 P3 from 7 agents. All 6 resolved. Top findings: stale docstring, missing runtime type guard, cross-module invariant test, critique_report MCP save gap (pre-existing), 2 test coverage gaps.

## Files to Scrutinize

| File | What changed | Risk area |
|------|-------------|-----------|
| `decompose.py` | `NOVELTY_INSTRUCTION_TEMPLATE` + system prompt variable + runtime type guard | Prompt injection via `.format()` — validated int only |
| `modes.py` | `novelty_queries: int` field + validation | Magic number 3 coupled to MAX_SUB_QUERIES via comment (mitigated with invariant test) |
| `mcp_server.py` | `get_critique_history` tool + `save_critique` in `critique_report` | META_DIR private import, boundary catch-all |
| `agent.py` | Single-line `novelty_queries` threading | Must stay in sync with mode field |
| `results.py` | `ModeInfo.novelty_queries` field | Must mirror ResearchMode field |

## Plan Reference

`docs/plans/2026-04-23-feat-novelty-decomposition-mcp-cost-critique-plan.md`
