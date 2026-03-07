# Review Context — Research Agent

## Risk Chain

**Plan risk:** "Double-Haiku path (iterate planning + relevance scoring) not tested end-to-end"

**Plan mitigation:** Item 5 added a dedicated e2e routing test verifying both `planning_model` and `relevance_model` route to `AUTO_DETECT_MODEL`.

**Work risk (from Feed-Forward):** "Whether `generate_followups` MCP tool needs its own `query` parameter or should extract it from report metadata."

**Review resolution:** 0 code bugs, coverage gaps only. Zero P1s. Two fix batches added edge-case tests (overlap boundary, MCP instructions, defensive copy mutation, real-code-path iteration_sections).

**Compound lesson:** Batch small deferred items into housekeeping cycles every 3-5 cycles. Validate every LLM output path at introduction time. Expose structured data alongside concatenated strings.

## Files to Scrutinize

| File | What changed | Risk area |
|------|-------------|-----------|
| `research_agent/search.py` | Added `validate_query_list()` to `refine_query()` | 0.8 overlap threshold (intentionally different from 0.6 in iterate.py) |
| `research_agent/mcp_server.py` | New `generate_followups` tool + instructions update | MCP instructions string manually maintained — no parity lint |
| `research_agent/results.py` | `iteration_sections` (tuple) + `source_counts` (dict) fields | Defensive copy on dict, direct return on tuple |
| `research_agent/agent.py` | Populates both new fields + `_iteration_sections` list | Mutation safety of internal list before tuple conversion |

## Cross-Tool Review Protocol

Codex is an independent second-opinion agent in this workflow. For reviews:
1. Run Codex `review-branch-risks` first (independent findings)
2. Then run Claude Code `/workflows:review` (compound review with learnings researcher)
3. Merge both finding sets, deduplicate, and apply fix ordering per CLAUDE.md rules

## Plan Reference

`docs/plans/2026-03-06-refactor-cycle-22-quick-wins-plan.md`
