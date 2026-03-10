---
status: deferred
priority: p2
issue_id: "123"
tags: [code-review, agent-native, mcp]
dependencies: []
unblocks: []
sub_priority: 5
---

# MCP Server Missing --cost and --critique-history Tool Equivalents

## Problem Statement

Two CLI capabilities have no MCP tool equivalent:
1. `--cost` (`cli.py:250-252`) — shows estimated costs per mode
2. `--critique-history` (`cli.py:255-261`) — shows aggregated critique patterns

This means agents cannot access cost estimates in a dedicated format or review their own performance history.

**Found by:** Agent-Native Reviewer
**Note:** Pre-existing gap, not a regression from Cycle 26. Flagged for future work.

## Findings

- `list_research_modes` partially covers cost info (includes `cost_estimate` in output), so the `--cost` gap is small
- `--critique-history` has no partial coverage — agents are blind to their own quality trends
- Agent-native score: 7/9 user-facing capabilities are agent-accessible

## Proposed Solutions

### Option A: Add both tools in a future housekeeping cycle

Add `show_costs` and `get_critique_history` MCP tools. Both are thin wrappers over existing functions.

- **Pros:** Closes parity gap completely
- **Cons:** Two more tools to maintain
- **Effort:** Small (each is ~15 lines)
- **Risk:** Low

### Option B: Enrich list_research_modes output only

Improve cost display in `list_research_modes` and skip the dedicated tool. Add `get_critique_history` only.

- **Pros:** Avoids a dedicated cost tool
- **Cons:** Less discoverable for agents
- **Effort:** Small
- **Risk:** Low

## Technical Details

- **Affected files:** `research_agent/mcp_server.py`

## Acceptance Criteria

- [ ] Agents can access cost estimates
- [ ] Agents can access critique history
- [ ] Lint script still passes after adding tools
