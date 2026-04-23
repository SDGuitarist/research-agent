---
status: resolved
priority: p2
issue_id: "135"
tags: [code-review, agent-native, mcp, pre-existing, cycle-31]
dependencies: []
unblocks: []
sub_priority: 5
---

# 135 - MCP critique_report tool does not persist critiques to disk

## Problem Statement

When an agent calls `critique_report` via MCP, the critique result is returned but never saved to disk. The CLI counterpart (`cli.py:272-273`) calls `save_critique(result, META_DIR)` after `critique_report_file()`. This means agent-initiated standalone critiques are invisible to `get_critique_history`, breaking the feedback loop.

**Pre-existing gap** -- not introduced by Cycle 31, but now more visible because `get_critique_history` was added. An agent following the recommended workflow (run_research -> critique_report -> get_critique_history) would find that standalone re-critiques via MCP don't accumulate.

## Findings

- **Source:** agent-native-reviewer
- **Location:** `research_agent/mcp_server.py:176-218` (missing save_critique call)
- **CLI counterpart:** `research_agent/cli.py:272-273` (has save_critique call)

## Proposed Solution

Add `save_critique(result, META_DIR)` to the MCP `critique_report` tool after getting the result, matching CLI behavior. Import `save_critique` from the critique module and `META_DIR` from agent (same pattern as `get_critique_history`).

- **Effort:** Small (~3 lines)
- **Risk:** Low -- adds file I/O inside the existing try/except boundary

## Acceptance Criteria

- [ ] MCP `critique_report` persists critiques to disk
- [ ] `get_critique_history` reflects agent-initiated critiques
- [ ] All tests pass
