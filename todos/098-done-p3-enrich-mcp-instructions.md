---
status: done
priority: p3
issue_id: "098"
tags: [code-review, agent-native, documentation]
dependencies: []
unblocks: []
sub_priority: 3
---

# Enrich MCP Server Instructions Field

## Problem Statement

The `FastMCP` constructor's `instructions` field is a single sentence. This is the equivalent of a system prompt for MCP clients. A richer instruction would improve discoverability for agents connecting for the first time.

## Findings

- **Source:** agent-native-reviewer
- **File:** `research_agent/mcp_server.py`, lines 15-22

## Proposed Solutions

### Option A: Expand instructions with workflow guidance (Recommended)
```python
instructions=(
    "Research agent that searches the web and generates structured markdown reports. "
    "Use list_research_modes to see available modes before running research. "
    "Use list_contexts to discover domain-specific context files. "
    "Reports auto-save for standard/deep modes — use list_saved_reports to find them. "
    "Set 'cwd' in your MCP client config to the research-agent project root."
)
```
- **Effort:** Small (copy change)
- **Risk:** None

## Acceptance Criteria

- [ ] Instructions mention all 5 tools and recommended workflow
- [ ] Set 'cwd' instruction preserved

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-28 | Created from agent-native-reviewer | Copy-only improvement |
