---
status: pending
priority: p3
issue_id: "130"
tags: [code-review, mcp, temperature, cycle-27]
dependencies: ["129"]
unblocks: []
sub_priority: 1
---

# 130 - Temperature settings invisible in `list_research_modes` MCP output

## Problem Statement

The `ModeInfo` dataclass correctly includes all three temperature fields, and `list_modes()` populates them. But `list_research_modes` in the MCP server formats output without including temperature values. MCP agents cannot discover what temperature settings each mode uses.

## Findings

- **Source:** Agent-native reviewer
- **Location:** `research_agent/mcp_server.py:275-290` (list_research_modes formatting)
- **Data layer:** Already correct — `results.py:ModeInfo` has the fields

## Proposed Solution

Add temperature info to the formatted output string, e.g.:
```python
f"temps: planning={m.planning_temperature}, summarize={m.summarize_temperature}, synthesis={m.synthesis_temperature}"
```

- Effort: Small (3-4 lines)

## Acceptance Criteria

- [ ] `list_research_modes` output includes temperature values for each mode
