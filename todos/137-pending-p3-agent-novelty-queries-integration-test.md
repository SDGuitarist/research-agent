---
status: resolved
priority: p3
issue_id: "137"
tags: [code-review, testing, integration, cycle-31]
dependencies: []
unblocks: []
sub_priority: 2
---

# 137 - No integration test that agent.py threads novelty_queries to decompose_query

## Problem Statement

The test suite thoroughly covers `ResearchMode.novelty_queries` validation and `decompose_query(novelty_queries=N)` prompt construction, but no test verifies that `agent.py:477` actually passes `self.mode.novelty_queries` to `decompose_query`. If that single line were deleted, all unit tests would still pass.

## Findings

- **Source:** architecture-strategist
- **Location:** `research_agent/agent.py:477`, `tests/test_agent.py` (no assertion for novelty_queries threading)

## Proposed Solution

Add a mock assertion in the existing agent test suite that verifies `decompose_query` is called with `novelty_queries=mode.novelty_queries`.

- **Effort:** Small (add assertion to existing test)

## Acceptance Criteria

- [ ] Test verifies decompose_query receives novelty_queries from the mode
- [ ] All tests pass
