---
status: complete
priority: p2
issue_id: "106"
tags: [code-review, testing, agent-native]
dependencies: []
unblocks: []
sub_priority: 5
---

# MCP server tests missing for skip_iteration and iteration_status

## Problem Statement

`TestRunResearchParams` tests `skip_critique` and `max_sources` pass-through but has no test for `skip_iteration`. The response header test doesn't verify `iteration_status` rendering.

## Findings

- **agent-native-reviewer**: P2 — boundary test coverage gap

**Location:** `tests/test_mcp_server.py`

## Proposed Solutions

### Option A: Add two boundary tests (Recommended)
1. Test `skip_iteration=True` is passed through to `run_research_async`
2. Test `iteration_status="completed"` produces `Iteration: completed` in response

- **Pros:** Covers MCP boundary for new parameters
- **Cons:** None
- **Effort:** Small
- **Risk:** None

## Acceptance Criteria

- [ ] Test verifying `skip_iteration` pass-through
- [ ] Test verifying `iteration_status` in response header
