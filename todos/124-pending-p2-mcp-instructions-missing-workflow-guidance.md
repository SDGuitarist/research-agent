---
status: resolved
priority: p2
issue_id: "124"
tags: [code-review, agent-native, mcp]
dependencies: []
unblocks: []
sub_priority: 6
---

# MCP Instructions String Lacks Workflow Guidance

## Problem Statement

The MCP instructions string tells agents what each tool does individually but not how to compose them for common workflows. An agent receiving these instructions would not know the typical sequence: list_research_modes -> list_contexts -> run_research -> critique_report -> generate_followups.

**Found by:** Agent-Native Reviewer
**Note:** Pre-existing gap, not a regression from Cycle 26.

## Findings

- Each tool gets a "Use X to Y" sentence — good for discoverability
- No guidance on ordering, dependencies, or common patterns
- Agents must infer the workflow from tool names alone

## Proposed Solutions

### Option A: Add a workflow hint sentence (Recommended)

Append to the instructions string:
```
"Typical workflow: list_research_modes to choose a mode, then run_research, then critique_report to evaluate quality, then generate_followups for next steps."
```

- **Pros:** One sentence, high leverage for agent behavior
- **Cons:** Instructions string grows slightly
- **Effort:** Small
- **Risk:** Low

## Technical Details

- **Affected files:** `research_agent/mcp_server.py` (instructions string)

## Acceptance Criteria

- [ ] Instructions string includes workflow guidance
- [ ] Lint script still passes
