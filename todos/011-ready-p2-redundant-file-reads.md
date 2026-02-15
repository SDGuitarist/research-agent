---
status: ready
triage_reason: "Accepted — redundant disk reads and YAML parses per run"
priority: p2
issue_id: "011"
tags: [code-review, performance]
dependencies: []
---

# Redundant file reads (load_full_context, load_schema)

## Problem Statement

`load_full_context()` is called 2-3 times per run (via `load_search_context` and `load_synthesis_context`). `load_schema()` is called twice (pre-research and post-research). The files don't change during a run.

## Findings

- **Performance oracle**: Two disk reads + YAML parses for schema per run.
- **Architecture strategist**: Could reuse `self._current_schema_result` in `_update_gap_states`.

**Files:** `research_agent/context.py:89,103` and `research_agent/agent.py:88,189`

## Proposed Solutions

### Option A: Cache context at agent level (Recommended)
Store context result on `self` after first load, reuse for subsequent calls.
- **Effort**: Small | **Risk**: Low

### Option B: Reuse schema_result in _update_gap_states
Use `self._current_schema_result` instead of re-loading from disk.
- **Effort**: Small | **Risk**: Low

## Acceptance Criteria

- [ ] `load_full_context()` called at most once per run
- [ ] `load_schema()` not redundantly called
- [ ] All tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-15 | Created from code review | 2/7 agents flagged redundant I/O |
