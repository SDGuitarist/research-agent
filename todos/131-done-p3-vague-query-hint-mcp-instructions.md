---
status: pending
priority: p3
issue_id: "131"
tags: [code-review, mcp, documentation, cycle-27]
dependencies: []
unblocks: []
sub_priority: 2
---

# 131 - Vague query behavior not documented in MCP instructions

## Problem Statement

The MCP instructions string does not mention that vague queries will be rejected. Agents discover the rejection only after hitting it. The error message is well-written and actionable, so agents can recover, but a hint would prevent unnecessary round-trips.

## Findings

- **Source:** Agent-native reviewer
- **Location:** `research_agent/mcp_server.py:16-29` (instructions string)

## Proposed Solution

Add one sentence to the instructions string:
```
"Queries must contain at least 2 specific, non-generic words -- vague queries like 'stuff' or 'best things' will be rejected with a suggestion."
```

- Effort: Small (1 line)

## Acceptance Criteria

- [ ] MCP instructions mention vague query rejection
- [ ] MCP lint script still passes
