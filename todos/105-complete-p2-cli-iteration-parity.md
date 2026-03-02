---
status: complete
priority: p2
issue_id: "105"
tags: [code-review, agent-native, parity]
dependencies: []
unblocks: []
sub_priority: 4
---

# CLI missing `--no-iteration` flag and iteration status display

## Problem Statement

The MCP server exposes `skip_iteration` and surfaces `iteration_status` in the response header, but the CLI has neither a `--no-iteration` flag nor any display of iteration status. This is an inverted parity gap — agents can do things CLI users cannot.

## Findings

- **agent-native-reviewer**: P2 — inverted parity gap (two items)

**Location:** `research_agent/cli.py` — argparse section and post-research output

## Proposed Solutions

### Option A: Add both flag and status display (Recommended)
1. Add `--no-iteration` argparse flag
2. Pass through to `ResearchAgent(skip_iteration=args.no_iteration)`
3. Print iteration status after critique summary

- **Pros:** Full bidirectional parity
- **Cons:** None
- **Effort:** Small
- **Risk:** None

## Acceptance Criteria

- [ ] `--no-iteration` flag added to argparse
- [ ] Flag threaded to ResearchAgent constructor
- [ ] Iteration status printed to stderr when not "skipped"
