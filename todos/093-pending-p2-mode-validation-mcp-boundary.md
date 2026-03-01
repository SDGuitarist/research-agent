---
status: pending
priority: p2
issue_id: "093"
tags: [code-review, security, defense-in-depth]
dependencies: []
unblocks: []
sub_priority: 4
---

# No Mode Parameter Validation at MCP Boundary

## Problem Statement

The `run_research` MCP tool accepts `mode` as a free-form string with no validation at the server boundary. Invalid modes traverse the entire call stack before failing deep in `ResearchMode.from_name()`. This wastes API call budget (env checks, context resolution) on obviously invalid input.

## Findings

- **Source:** security-sentinel review
- **File:** `research_agent/mcp_server.py`, lines 26-30
- **Evidence:** `mode: str = "standard"` with no early validation

## Proposed Solutions

### Option A: Early validation with set check (Recommended)
```python
VALID_MODES = {"quick", "standard", "deep"}

async def run_research(query, mode="standard", context=None):
    if mode not in VALID_MODES:
        raise ToolError(
            f"Invalid mode: {mode!r}. Must be one of: {', '.join(sorted(VALID_MODES))}"
        )
```
- **Effort:** Small (4 lines)
- **Risk:** None — duplicates validation but fails faster with a better message

## Acceptance Criteria

- [ ] Invalid mode raises ToolError immediately at boundary
- [ ] Error message lists valid options
- [ ] Test for invalid mode still passes

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-28 | Created from security-sentinel review | Defense-in-depth pattern |
