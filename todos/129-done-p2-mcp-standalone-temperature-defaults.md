---
status: pending
priority: p2
issue_id: "129"
tags: [code-review, mcp, temperature, cycle-27]
dependencies: []
unblocks: ["130"]
sub_priority: 3
---

# 129 - MCP standalone tools use temperature=1.0 instead of pipeline defaults

## Problem Statement

The `critique_report` and `generate_followups` MCP tools call module functions directly without passing a temperature. These functions default to `temperature=1.0`, while the in-pipeline paths use `planning_temperature` (0.2) for followups and `planning_temperature` (0.2) for critique evaluation.

This means MCP agents get noisier, less deterministic results from the same functions.

## Findings

- **Source:** Agent-native reviewer
- **Locations:**
  - `research_agent/mcp_server.py:197` — `critique_report_file(client, path, model=DEFAULT_MODEL)` — no temperature
  - `research_agent/mcp_server.py:253` — `generate_followup_questions(...)` — no temperature
- **Plan note:** The plan explicitly accepted this ("MCP tools don't have a mode object"), but hardcoded sensible defaults would close the gap.

## Proposed Solutions

### Option A: Pass hardcoded temperature defaults in MCP tools
```python
# critique_report — evaluation/scoring task
result = critique_report_file(client, path, model=DEFAULT_MODEL, temperature=0.8)

# generate_followups — planning task
result = generate_followup_questions(..., temperature=0.2)
```
- Pros: 2-line fix, aligns MCP behavior with pipeline
- Cons: Hardcoded values could drift from ResearchMode defaults
- Effort: Small
- Risk: None

### Option B: Import defaults from ResearchMode
```python
from .modes import ResearchMode
_defaults = ResearchMode.standard()
temperature=_defaults.planning_temperature
```
- Pros: Single source of truth
- Cons: Couples MCP server to ResearchMode
- Effort: Small
- Risk: Low

## Recommended Action

Option A — simpler, and the values are stable (0.2 and 0.8).

## Acceptance Criteria

- [ ] `critique_report` MCP tool passes `temperature=0.8`
- [ ] `generate_followups` MCP tool passes `temperature=0.2`
- [ ] Existing MCP tests pass
