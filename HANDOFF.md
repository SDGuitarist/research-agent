# HANDOFF — Research Agent

**Date:** 2026-04-23
**Branch:** `main`
**Phase:** Cycle 31 PLAN COMPLETE. Ready for Codex plan review.

## Current State

Cycle 31 brainstorm + plan + deepening done. Two features planned:

1. **Novelty-biased decomposition** — `novelty_queries: int` field on `ResearchMode` (quick=0, standard=1, deep=2). Reframes existing sub-queries with novelty instruction via `NOVELTY_INSTRUCTION_TEMPLATE` module-level constant in `decompose.py`. Appended after last rule bullet in system prompt.

2. **MCP `get_critique_history` tool** — Wraps `load_critique_history(META_DIR)` with `except Exception` boundary catch-all. Closes #123 parity gap.

`show_costs` MCP tool dropped during deepening (redundant with `list_research_modes`).

Plan deepened by 9 review agents. Key improvements: C30 diversity gate interaction risk documented, prompt constant pattern, boundary catch-all, MCP controllability documented as mode-locked.

## Key Artifacts

| Phase | Location |
|-------|----------|
| Brainstorm | `docs/brainstorms/2026-04-22-cycle-31-novelty-decomposition-mcp-tools-brainstorm.md` |
| Plan | `docs/plans/2026-04-23-feat-novelty-decomposition-mcp-cost-critique-plan.md` |
| Codex Handoff | `docs/plans/2026-04-23-codex-plan-review-handoff.md` |

## Deferred Items

- **ANTHROPIC_ERRORS consumption at 10+ call sites** — mechanical replacement for micro-cycle
- **`show_costs` MCP tool** — intentionally dropped (covered by `list_research_modes`)
- **A/B live validation** — run `scripts/validate_cutoff_ab.py` when API keys renewed
- **Session 4 live tier-label validation (C29)** — run deep-mode query when API key replaced
- **One-sentence vs cumulative chunk summary** — if deep-mode chunk 3+ summaries show orphaned references, upgrade to cumulative
- **Diversity gate threshold tuning** — monitor short_report frequency for niche topics after API key renewal
- **`META_DIR` promotion to public location** — 3 review agents flagged, accepted as existing pattern
- **`to_mode_info()` method on ResearchMode** — eliminates manual ModeInfo field syncing

## Three Questions

1. **Hardest decision?** Dropping `show_costs` — brainstorm included it, but 3/9 deepening agents independently flagged redundancy.
2. **What was rejected?** Boolean `novelty_bias` (simplicity reviewer's recommendation) — int preserved for standard-vs-deep granularity.
3. **Least confident?** Diversity gate interaction with novelty sub-queries AND prompt wording generalization across query domains. Both need live A/B testing.

## Prompt for Next Session

### After Codex Review (no changes needed)

```
Read docs/plans/2026-04-23-feat-novelty-decomposition-mcp-cost-critique-plan.md.
Implement Session 1: Novelty decomposition — field + prompt + threading.
Relevant files: modes.py, results.py, __init__.py, decompose.py, agent.py, mcp_server.py, tests/test_modes.py, tests/test_decompose.py.
Do only Session 1. After committing, stop and say DONE. Do NOT proceed to Session 2.
```

### After Codex Review (changes needed)

```
Read docs/plans/2026-04-23-feat-novelty-decomposition-mcp-cost-critique-plan.md.
Codex review findings: [paste findings here].
Update the plan to address findings, then implement Session 1.
Do only Session 1. After committing, stop and say DONE.
```
