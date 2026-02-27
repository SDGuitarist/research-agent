---
status: done
priority: p2
issue_id: "047"
tags: [code-review, architecture]
dependencies: ["043"]
---

# P2: Move `RETRY_SOURCES_PER_QUERY` into `ResearchMode`

## Problem Statement

`RETRY_SOURCES_PER_QUERY = 3` is a module-level constant in `agent.py:43`. The project convention (per CLAUDE.md: "Frozen dataclasses for modes: All mode parameters in one place") requires all tuning knobs to live in `ResearchMode`. Quick mode searching 3 sources per retry query (up to 9 total) would more than double its source budget.

## Findings

- Flagged by: architecture-strategist
- Depends on #043 (quick mode guard) — if quick mode is guarded, the per-mode value matters less

## Proposed Solutions

### Option A: Add `retry_sources_per_query` field to `ResearchMode`
- Quick: 2 (or 0 if guarded), Standard: 3, Deep: 5
- Pros: Consistent with project convention
- Cons: Adds a field to ResearchMode
- Effort: Small
- Risk: Low

## Technical Details

- **File:** `research_agent/agent.py:43`, `research_agent/modes.py`

## Acceptance Criteria

- [ ] `RETRY_SOURCES_PER_QUERY` removed from `agent.py` module level
- [ ] `ResearchMode` has `retry_sources_per_query` field with per-mode values
- [ ] `_try_coverage_retry` reads from `self.mode.retry_sources_per_query`
- [ ] All tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-25 | Created from review | — |
