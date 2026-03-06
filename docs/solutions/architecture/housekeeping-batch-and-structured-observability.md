---
title: "Housekeeping Batch Pattern and Structured Observability"
category: architecture
cycle: 22
date: 2026-03-06
tags: [housekeeping, validation, mcp-parity, observability, structured-data, model-routing]
related:
  - architecture/tiered-model-routing-planning-vs-synthesis.md
  - architecture/agent-native-return-structured-data.md
  - security/mcp-server-boundary-protection-and-agent-parity.md
  - performance-issues/redundant-retry-evaluation-and-code-deduplication.md
---

# Housekeeping Batch Pattern and Structured Observability

## Prior Phase Risk

> "Whether the review coverage is truly complete. Batch 1 added edge-case tests for Items 1, 2, 5. Batch 2 verified and documented Items 3, 4. But none of the batches re-examined the overlap threshold (0.8 vs 0.6) flagged in Item 1's review focus — it was accepted as-is."

**Resolution:** The 0.8 overlap threshold for `refine_query` is intentionally different from the 0.6 used in `iterate.py`. Refinement should stay close to the original query (filling gaps, not diverging), while iteration queries are expected to explore further. The plan documented this rationale explicitly. Accepting as-is was the correct call.

## Problem

After Cycles 20-21 shipped major features (iterative research, tiered model routing), five small improvements were deferred individually. None justified a full brainstorm-plan-work-review-compound loop, but collectively they represented growing debt:

1. `refine_query()` was the last unvalidated LLM output path
2. `generate_followup_questions()` had no MCP surface — agents couldn't ask "what next?"
3. Iteration mini-reports were concatenated into `report` with no structured access
4. Per-query source counts were logged but not exposed programmatically
5. The double-Haiku path (planning + relevance on Haiku) had no e2e test

## Solution

### Batch Housekeeping Cycle

Group small, independent items into a single "quick wins" cycle. Each item gets its own commit but shares one plan, one review, and one compound phase. This is efficient for items that:
- Follow established patterns (no design decisions needed)
- Are independent (no ordering dependencies between items)
- Are small (~50 lines each)

### What Was Shipped

**1. Validate `refine_query()` output** (`search.py`)
- Added `validate_query_list()` call after LLM returns refined query
- Constants: `MIN_REFINED_WORDS = 3`, `MAX_REFINED_WORDS = 10`
- Overlap threshold: 0.8 (lenient — refinement should relate to original)
- Falls back to original query on rejection

**2. `generate_followups` MCP tool** (`mcp_server.py`)
- Standalone tool following `critique_report` pattern
- Uses `AUTO_DETECT_MODEL` (Haiku) — follow-up generation is a planning task
- Input validation: filename check + `num_questions` clamped to 1-5
- Added to MCP `instructions` string

**3. `iteration_sections` on ResearchResult** (`results.py`, `agent.py`)
- `tuple[str, ...]` field, default `()`
- Populated in `_run_iteration()` from the mini-report accumulation loop
- Backward compatible — `report` still contains full text

**4. `source_counts` on ResearchResult** (`results.py`, `agent.py`)
- `dict[str, int]` mapping query string to source count
- Property returns `dict(self._source_counts)` (defensive copy)
- Populated in `_research_with_refinement` and `_research_deep`

**5. Double-Haiku e2e routing test** (`test_agent.py`)
- Integration test verifying `decompose_query` gets `planning_model` and `evaluate_sources` gets `relevance_model`, both set to `AUTO_DETECT_MODEL`

### Review Outcome

Zero code bugs found. Review identified coverage gaps only, addressed in two fix batches:
- Batch 1: Edge-case tests for overlap boundary, MCP instructions, deep mode source_counts, model divergence assertions
- Batch 2: Verified defensive copy pattern with mutation test, real-code-path iteration_sections test

## Risk Resolution

| Flagged Risk | What Happened | Lesson |
|---|---|---|
| 0.8 vs 0.6 overlap threshold | Accepted as-is — refinement intentionally stays close to original | Document threshold rationale in the plan so reviewers don't re-litigate |
| `source_counts` returns copy vs. `iteration_sections` returns tuple directly | Verified as correct — mutable dict needs copy, immutable tuple doesn't | Defensive copy for mutable properties, direct return for immutable ones |
| `generate_followups` needs explicit `query` param | Confirmed simpler than parsing from report metadata | Start with explicit params; add convenience later if needed |

## Prevention Strategies

- **Validate every LLM output path at introduction time.** When adding any new LLM call that returns structured data, add validation in the same commit. Never defer.
- **Expose structured data whenever you concatenate.** If you build a result by accumulating items in a loop, store the individual items as a tuple/dict field alongside any concatenated summary.
- **Audit observability on every new pipeline stage.** When adding a pipeline stage that processes N items, expose the count or per-item metadata on the result object.
- **MCP tool parity as a checklist item.** When adding user-facing functionality, check both CLI and MCP surfaces in the same cycle.
- **Batch housekeeping every 3-5 cycles.** Group small deferred items into a dedicated quick-wins cycle to prevent debt accumulation.

## Testing Patterns

- **E2e model routing test for every new `*_model` field.** Mock the client, assert the model string propagates to the actual API call.
- **Property mutation test for defensive copies.** Mutate the returned value, assert internal state unchanged.
- **Coverage gap audit after review.** "Are there untested branches in new code?" as a standard review checklist item.

## Three Questions

1. **Hardest pattern to extract from the fixes?** The relationship between "batch housekeeping cycle" as a workflow pattern and "structured observability" as a code pattern. They're both about surfacing what's implicit — one at the project level (deferred items), one at the code level (logged-but-not-exposed data). Chose to document both in one solution since they co-occurred.

2. **What did you consider documenting but left out, and why?** Considered a standalone "query validation patterns" doc since `validate_query_list` now covers 4 call sites with different thresholds. Left it out because the existing `redundant-retry-evaluation-and-code-deduplication.md` already documents the extraction, and the threshold rationale is specific to each call site (documented in their respective plans).

3. **What might future sessions miss that this solution doesn't cover?** The MCP instructions string is manually maintained — adding a new tool requires updating both the `@mcp.tool` decorator and the `instructions` field. There's no automated check that all tools appear in instructions. A lint rule or test asserting parity would close this gap.
