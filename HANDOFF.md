# HANDOFF — Research Agent

**Date:** 2026-04-23
**Branch:** `feat/31-novelty-decomposition-mcp-critique`
**Phase:** Cycle 31 REVIEW + FIXES COMPLETE. Ready for compound phase.

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

## Review Results

**Review date:** 2026-04-23
**Agents used:** 7 (kieran-python, security-sentinel, architecture-strategist, pattern-recognition, agent-native, learnings-researcher, code-simplicity)
**Tests:** 1116 passing | MCP lint: 8/8

### Findings Summary

| ID | Sev | Description | Status |
|----|-----|-------------|--------|
| 132 | P2 | decompose_query docstring missing temperature + novelty_queries params | pending |
| 133 | P2 | No runtime type guard on novelty_queries in decompose_query | pending |
| 134 | P2 | Cross-module invariant test for novelty_queries vs MAX_SUB_QUERIES | pending |
| 135 | P2 | critique_report MCP doesn't save critiques (pre-existing) | pending |
| 136 | P3 | Missing ContextResult.empty() test for get_critique_history | pending |
| 137 | P3 | No integration test for agent.py novelty_queries threading | pending |
| 123 | P2 | MCP missing cost/critique-history tools | done (this PR) |

**0 P1 findings. No merge blockers.**

### Discarded / Accepted Risks

- `except Exception` catch-all in get_critique_history: all 7 agents validated as consistent with established MCP boundary pattern
- TOCTOU symlink gap in critique file loading: pre-existing, requires local write access, strict YAML schema validation limits exploitation
- META_DIR private import by 3 consumers: plan already tracks as deferred housekeeping
- ModeInfo/ResearchMode manual sync: plan already defers to_mode_info() method
- Test redundancy (simplicity reviewer): optional polish, not actionable

## Three Questions

1. **Hardest judgment call in this review?** Whether to create a todo for the `critique_report` save gap (135). It's pre-existing — not introduced by this PR — but now more visible because `get_critique_history` was added. An agent following the recommended workflow would find standalone re-critiques invisible. P2 felt right because it affects the feedback loop this PR explicitly enables.
2. **What did you consider flagging but chose not to, and why?** The `except Exception` boundary catch-all. The HANDOFF flagged this as a risk, but every agent that reviewed it confirmed it follows the established pattern used by all 4 existing MCP tools. Changing one without changing all would be inconsistent.
3. **What might this review have missed?** Whether novelty-framed sub-queries interact badly with the C30 diversity gate in practice. The architectural safety nets are in place (relevance scoring, diversity gate, source tier caps), but contrarian perspectives may score lower on relevance, causing more SHORT_REPORT downgrades for niche queries. This is a runtime quality question requiring live A/B testing.

### Fix Phase Results

4 fix commits: `94df004`, `c87ac0b`, `329c469`, `622522a`
- Batch 1: Docstring + type guard in decompose.py (132, 133)
- Batch 2: Cross-module invariant test in test_modes.py (134)
- Batch 3: critique_report save_critique in mcp_server.py (135)
- Batch 4: ContextResult.empty() + agent threading tests (136, 137)

**Tests:** 1118 passing (was 1116) | MCP lint: 8/8

## Prompt for Next Session

```
Read HANDOFF.md for context. This is research-agent on branch
feat/31-novelty-decomposition-mcp-critique.
Cycle 31 review + fixes complete. All 6 findings resolved.
Run /workflows:compound to document this cycle and propagate learnings.
```
