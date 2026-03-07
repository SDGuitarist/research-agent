# Codex Review Handoff — Cycle 22 Quick Wins

**Branch:** `refactor/cycle-22-quick-wins`
**Base:** `main`
**Date:** 2026-03-06
**Tests:** 907 passing (`python3 -m pytest tests/ -v`)

## What This PR Does

Five independent housekeeping items deferred from Cycles 20-21. All are small, additive changes following established patterns.

## Items to Review

### 1. Validate `refine_query()` output (search.py)
- **Commit:** `07a1668 refactor(search): validate refine_query output with validate_query_list`
- **Files:** `research_agent/search.py`, `tests/test_search.py`
- **What:** After LLM returns a refined query string, validate it with `validate_query_list()` (3-10 words, 0.8 overlap threshold). Falls back to original query on rejection.
- **Review focus:** Is 0.8 overlap threshold correct? (Other paths use 0.6, but refinement should stay close to original.) Are the 3 new tests sufficient?

### 2. `generate_followups` MCP tool (mcp_server.py)
- **Commit:** `e24dd12 feat(mcp): add generate_followups tool for agent-native parity`
- **Files:** `research_agent/mcp_server.py`, `tests/test_mcp_server.py`
- **What:** Standalone MCP tool that generates follow-up research questions from a completed report. Uses Haiku (AUTO_DETECT_MODEL) for planning. Follows `critique_report` pattern.
- **Review focus:** Input validation (filename, num_questions clamping). Does the MCP instructions string include the new tool? Are the 2 tests sufficient?

### 3. `iteration_sections` field on ResearchResult (results.py, agent.py)
- **Commit:** `40541a5 feat(results): add iteration_sections field to ResearchResult`
- **Files:** `research_agent/results.py`, `research_agent/agent.py`, `research_agent/__init__.py`, `tests/test_agent.py`
- **What:** Tuple field exposing mini-report strings from iteration. Stored on `self._iteration_sections` in agent, wired through to `ResearchResult`.
- **Review focus:** Is the tuple populated correctly in `_run_iteration`? Backward compatibility (default `()`).

### 4. `source_counts` field on ResearchResult (results.py, agent.py)
- **Commit:** `3c755af feat(results): add source_counts field to ResearchResult`
- **Files:** `research_agent/results.py`, `research_agent/agent.py`, `research_agent/__init__.py`, `tests/test_agent.py`
- **What:** Dict mapping query string to source count. Populated in `_research_with_refinement` and `_research_deep` after each `search()` call. Sub-queries tracked as combined `(sub-queries)` entry.
- **Review focus:** The `source_counts` property returns `dict(self._source_counts)` (defensive copy). Is this the right pattern vs. returning the internal dict? Does it populate correctly in both research paths? Is the single test sufficient?
- **Flagged risk from work phase:** "source_counts property returns a copy which is safe but slightly different from other properties like iteration_sections which return the internal tuple directly."

### 5. Double-Haiku e2e routing test (test_agent.py)
- **Commit:** `5b20e2d test(agent): add double-Haiku e2e routing test`
- **Files:** `tests/test_agent.py`
- **What:** Integration test verifying `decompose_query` gets `planning_model` and `evaluate_sources` gets `mode.relevance_model`, both set to `AUTO_DETECT_MODEL` (Haiku).
- **Review focus:** Does the test actually exercise the double-Haiku path end-to-end, or just check kwargs? Are the mock boundaries correct?

## Non-code Commits (lower priority)

- `9397c64 docs(22): compound Cycle 21, add Cycle 22 quick wins plan` — plan doc + lessons learned
- `f6910d6 docs(22): update plan acceptance criteria and handoff for Session 2` — checklist updates
- `1cf7a69 docs: propagate Codex integration to learning surfaces` — learning docs
- `bae5b06 docs: add AGENTS.md for Codex repo instructions` — this repo's Codex instructions

## How to Review

```bash
git diff main..refactor/cycle-22-quick-wins -- research_agent/ tests/
```

Review each item independently. For each, check:
1. **Correctness** — Does the code do what the plan says?
2. **Safety** — Any prompt injection vectors, bare exceptions, or missing validation?
3. **Tests** — Do the tests cover the happy path and key edge cases?
4. **Consistency** — Does the new code follow existing patterns in the codebase?

## Key Codebase Conventions

- Mock where the name is imported FROM, not where it's used
- Frozen dataclasses for mode configuration (`ResearchMode`)
- Agent state as private attrs with public properties (e.g., `_last_source_count` / `last_source_count`)
- Three-layer prompt injection defense: sanitize + XML boundaries + system prompt
- `validate_query_list()` is the shared query validation gate

## Plan Reference

Full plan with rationale: `docs/plans/2026-03-06-refactor-cycle-22-quick-wins-plan.md`
