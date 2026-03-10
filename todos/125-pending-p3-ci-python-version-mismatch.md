---
status: resolved
priority: p3
issue_id: "125"
tags: [code-review, ci]
dependencies: []
unblocks: []
sub_priority: 1
---

# CI Workflow Uses Python 3.12 While Project Uses 3.14

## Problem Statement

`.github/workflows/mcp-lint.yml:15` pins Python 3.12 while the project uses Python 3.14 locally (per CLAUDE.md). The `pyproject.toml` floor is `>=3.10`.

**Found by:** Performance Oracle, Architecture Strategist, Agent-Native Reviewer

## Findings

- The lint script is simple enough that version skew is unlikely to matter
- If `mcp_server.py` ever uses 3.13+ features at import time, CI would break confusingly
- The plan explicitly documented this choice: "single version — this is a lint check, not a compatibility test"

## Proposed Solutions

### Option A: Accept and document (Recommended for now)

Add a YAML comment explaining the choice. Revisit when a broader CI test workflow is added.

- **Effort:** Trivial
- **Risk:** None

### Option B: Bump to 3.14

- **Pros:** Matches local dev
- **Cons:** 3.14 may not be available on all GitHub runners yet
- **Effort:** Small

## Technical Details

- **Affected files:** `.github/workflows/mcp-lint.yml`

## Acceptance Criteria

- [ ] Decision documented (comment or plan)
