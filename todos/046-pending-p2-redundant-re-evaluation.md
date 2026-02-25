---
status: done
priority: p2
issue_id: "046"
tags: [code-review, performance]
dependencies: []
---

# P2: Retry re-evaluates ALL summaries redundantly

## Problem Statement

After a coverage retry, `_try_coverage_retry()` at `agent.py:492-500` calls `evaluate_sources()` on the **entire combined list** (existing + new summaries). This means existing summaries get scored twice — once in the initial evaluation and again after retry. Each `score_source()` call is one Claude API call.

In standard mode: initial ~30 scoring calls + retry re-scoring ~57 total = ~30 redundant calls, ~$0.06 waste and ~15 seconds extra latency.

## Findings

- Flagged by: performance-oracle
- Only new summaries need scoring; existing scores should be preserved
- Would require a merge helper for `RelevanceEvaluation`

## Proposed Solutions

### Option A: Score only new summaries, merge evaluations (Recommended)
Score new summaries separately, then merge surviving sources from both evaluations and re-derive the gate decision.
- Pros: Eliminates ~30 redundant API calls
- Cons: Requires a `RelevanceEvaluation` merge helper, moderate complexity
- Effort: Medium
- Risk: Medium (gate decision logic must be replicated correctly)

### Option B: Accept the redundancy
The retry path is rare (only on insufficient/short) and the cost is manageable.
- Pros: No code change
- Cons: Wastes API calls and time when retry fires
- Effort: None
- Risk: None

## Technical Details

- **File:** `research_agent/agent.py:488-501`
- **Related:** `research_agent/relevance.py:evaluate_sources` — scoring logic

## Acceptance Criteria

- [ ] Retry only scores new summaries
- [ ] Gate decision correctly reflects combined surviving sources
- [ ] Cost per retry reduced by ~50%
- [ ] All tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-25 | Created from review | May accept Option B if merge complexity is high |
