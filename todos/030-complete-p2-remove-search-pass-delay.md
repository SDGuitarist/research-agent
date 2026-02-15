---
status: complete
priority: p2
issue_id: "030"
tags: [code-review, performance]
dependencies: []
---

# Unnecessary Search Pass Delay

## Problem Statement

`agent.py` has a 1.0-1.5s `asyncio.sleep()` between search passes (lines ~511-512). Query refinement already provides natural spacing between API calls, making this delay unnecessary latency.

## Findings

- **Source:** Performance Oracle agent
- **Location:** `research_agent/agent.py:511-512`

## Proposed Solutions

### Option A: Remove the sleep (Recommended)
Delete the `asyncio.sleep()` call. Query refinement provides sufficient spacing.
- **Effort:** Small (10 min)

## Acceptance Criteria

- [ ] Sleep between search passes is removed
- [ ] Search still works correctly with multiple passes
- [ ] All tests pass
