# HANDOFF — Research Agent

**Date:** 2026-03-02
**Branch:** `main`
**Phase:** Cycle 21 plan complete — ready for deepen-plan, then work
**Last commit:** `672e1cc` — docs(20-compound): document parallel async synthesis patterns

## Current State

Cycle 21 **plan** for Tiered Model Routing is complete. Brainstorm was reviewed (document-review skill), then plan was written with full local research (repo-research-analyst + learnings-researcher). No code changes yet.

Key finding from research: **7 call sites** in agent.py, not 6 — `refine_query` is called twice (line ~933 and ~1003). All 6 target functions already accept `model` as a kwarg, so no module changes needed.

## Key Decisions

- **Scope:** Tier 1 only — 6 planning/classification calls move to Haiku
- **Approach:** Add `planning_model` field to `ResearchMode` frozen dataclass
- **Steps on Haiku:** decompose, refine_query, coverage_gaps, iterate queries, followup questions, self-critique
- **Steps on Sonnet:** summarize, relevance scoring, synthesis, skeptic agents
- **Quick mode:** Stays on Sonnet (no planning steps to move)
- **Estimated savings:** ~8-11% per standard/deep run

## Key Artifacts

| Phase | Location |
|-------|----------|
| Brainstorm | `docs/brainstorms/2026-03-02-tiered-model-routing-brainstorm.md` |
| Plan | `docs/plans/2026-03-02-feat-tiered-model-routing-plan.md` |

## Deferred Items

From Cycle 20 + this brainstorm:
- Tier 2: Haiku for relevance scoring (needs A/B comparison data)
- Tier 3: Haiku for summarization (deferred indefinitely — too risky)
- Standalone `generate_followups` MCP tool (agent-native parity)
- `iteration_sections: tuple[str, ...]` structured field on ResearchResult
- Per-query source count observability
- Double-sanitization idempotency risk (standing risk from Cycle 20)

## Three Questions (Plan Phase)

1. **Hardest decision?** Whether to validate `planning_model` in `__post_init__`. Decided against it — the existing `model` field has no validation, and adding it to one but not the other creates inconsistency.
2. **What was rejected?** A `--planning-model` CLI debug flag for verification. Verbose logging (`-v`) already shows which model is used — a dedicated flag adds complexity for a one-time check.
3. **Least confident about?** Whether the cost estimate updates are accurate. The brainstorm estimates (~11% standard, ~8% deep) are rough — actual savings depend on token counts per planning call, which vary by query complexity.

## Prompt for Next Session (Deepen Plan)

```
Read docs/plans/2026-03-02-feat-tiered-model-routing-plan.md. Run /deepen-plan to enhance the plan with parallel research. After deepen-plan is complete, stop.
```

## Prompt for Work Session (after deepen)

```
Read docs/plans/2026-03-02-feat-tiered-model-routing-plan.md. Run /workflows:work to implement. Single session — ~50 lines of changes. Relevant files: research_agent/modes.py, research_agent/agent.py, tests/test_modes.py. Do only the work phase — commit and stop.
```
