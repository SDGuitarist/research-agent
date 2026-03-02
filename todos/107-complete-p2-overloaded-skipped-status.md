---
status: complete
priority: p2
issue_id: "107"
tags: [code-review, quality, api-design]
dependencies: []
unblocks: []
sub_priority: 6
---

# Iteration status "skipped" overloaded for two meanings

## Problem Statement

`iteration_status = "skipped"` means both "iteration was never attempted" (quick mode, skip_iteration flag, insufficient_data gate) AND "iteration ran but found no new sources." API consumers cannot distinguish these cases.

## Findings

- **kieran-python-reviewer**: P2 — ambiguous for ResearchResult consumers
- **performance-oracle**: Related — truncate draft to also save tokens

**Location:** `research_agent/agent.py:870-872`

## Proposed Solutions

### Option A: Add "no_new_sources" status (Recommended)
When iteration ran but `iteration_sources_added == 0`, set status to `"no_new_sources"` instead of `"skipped"`.

- **Pros:** Consumers can distinguish "never tried" from "tried, nothing found"
- **Cons:** Fourth status value; update MCP header logic
- **Effort:** Small
- **Risk:** Low — additive change, default stays "skipped"

### Option B: Keep as-is
- **Pros:** Simpler
- **Cons:** Ambiguous for API consumers
- **Effort:** None

## Acceptance Criteria

- [ ] New status value distinguishes "tried, no results" from "never attempted"
- [ ] MCP header renders the new status correctly
- [ ] Tests updated for new status value
