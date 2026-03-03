---
status: done
priority: p3
issue_id: "118"
tags: [code-review, documentation, agent-native]
dependencies: ["116"]
unblocks: []
sub_priority: 2
---

# 118: Update run_research MCP docstring to mention tiered routing

## Problem Statement

The `run_research` MCP tool docstring in `mcp_server.py` describes cost estimates per mode but does not mention that planning steps use a cheaper model. An agent estimating costs or reasoning about latency has incomplete information. The cost estimates ("~$0.12" / "~$0.45" / "~$0.95") are also pre-tiered-routing numbers.

**Why it matters:** Agent comprehension of cost and latency behavior is incomplete without this context.

## Findings

- **Source:** Agent-native reviewer (Warning 3)
- **Evidence:** `research_agent/mcp_server.py:38-55`
- **Dependency:** Best done after 116 (ModeInfo update) so the routing info is also visible in `list_research_modes`

## Proposed Solutions

### Option A: Add one sentence to docstring (Recommended)
Add a note like: "Planning/classification steps (decompose, refine, gap analysis) use a lighter model for cost efficiency; synthesis and quality-critical steps use the full model."

- **Effort:** Trivial (1-2 lines)
- **Risk:** None

### Option B: Also update cost estimates
Update the cost estimate strings after collecting real usage data.

- **Pros:** Complete accuracy
- **Cons:** Need real data first (deferred in HANDOFF.md)
- **Effort:** Small, but blocked on data collection

## Acceptance Criteria

- [ ] `run_research` docstring mentions tiered model routing
- [ ] Cost estimates note that they are approximate

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-03-03 | Created from Cycle 21 review | Cost estimates deferred until real data collected |
