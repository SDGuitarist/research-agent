# HANDOFF — Research Agent

**Date:** 2026-03-06
**Branch:** `refactor/cycle-22-quick-wins`
**Phase:** Work complete (Session 2 of 2 done) → Review next

## Current Priority

- Goal: Fix Batch 2 code concerns from Codex review.
- Stop condition: Batch 2 items verified/documented, committed, pushed.
- Read next: `docs/reviews/cycle-22/CODEX-REVIEW-FINDINGS.md`

## Current State

Cycle 22 quick wins — all 5/5 items shipped + Batch 1 tests added. On feature branch `refactor/cycle-22-quick-wins` with 6 commits. 911 tests passing.

### Session 1 Commits
1. `refactor(search): validate refine_query output with validate_query_list` — 3-10 word validation, 0.8 overlap threshold
2. `feat(mcp): add generate_followups tool for agent-native parity` — standalone MCP tool using Haiku
3. `feat(results): add iteration_sections field to ResearchResult` — tuple of mini-report strings

### Session 2 Commits
4. `feat(results): add source_counts field to ResearchResult` — dict mapping query → source count, populated in both research paths
5. `test(agent): add double-Haiku e2e routing test` — verifies planning_model + relevance_model both route to Haiku

## Key Artifacts

| Phase | Location |
|-------|----------|
| Plan | `docs/plans/2026-03-06-refactor-cycle-22-quick-wins-plan.md` |
| Branch | `refactor/cycle-22-quick-wins` (5 commits ahead of main) |

## Three Questions

1. **Hardest implementation decision?** How to populate `source_counts` without refactoring `_search_sub_queries` return type. Chose to track counts at direct `search()` call boundaries (original query + refined query) plus a combined `(sub-queries)` entry. Per-sub-query counts would require changing the static method signature used in 4 places — not worth it for observability.

2. **What did you consider changing but left alone?** Considered making `_search_sub_queries` a regular method (not static) so it could write to `self._source_counts` directly with per-query granularity. Left it as a static method because the plan explicitly rejected this refactor, and the combined sub-query count still answers the key debugging question.

3. **Least confident about going into review?** The `source_counts` property returns a copy (`dict(self._source_counts)`) which is safe but slightly different from other properties like `iteration_sections` which return the internal tuple directly. Frozen tuples don't need copying; mutable dicts do. Reviewers should confirm this is the right pattern.

### Batch 1 Commit (Review Fixes)
6. `test(22): add Batch 1 review tests — edge cases and coverage gaps` — 4 test additions: overlap boundary, MCP instructions, deep mode source_counts, double-Haiku model divergence

## Next Phase

**Fix-batched (Batch 2)** — code concerns from Codex review.

### Prompt for Next Session

```
Read docs/reviews/cycle-22/CODEX-REVIEW-FINDINGS.md. Run Batch 2 (code concerns). Branch: refactor/cycle-22-quick-wins. 911 tests passing.

BATCH 2 (code concerns):
- Item 4: Verify source_counts defensive copy (dict()) is the right pattern — document why it differs from iteration_sections (tuple is already immutable)
- Item 3: Verify iteration_sections tuple is populated in _run_iteration (not just stored on self)

Relevant files: research_agent/agent.py, research_agent/results.py, tests/test_agent.py.

Do only Batch 2. Commit and stop.
```
