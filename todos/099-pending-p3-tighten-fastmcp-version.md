---
status: pending
priority: p3
issue_id: "099"
tags: [code-review, dependencies]
dependencies: []
unblocks: []
sub_priority: 4
---

# Tighten fastmcp Version Constraint

## Problem Statement

`pyproject.toml` specifies `fastmcp>=2.0,<4.0` — a wide range for a young library. FastMCP major version bumps could break the `Client` test fixture, change the `ToolError` import path, or alter transport behavior. The test suite would catch breakage, but only after it happens.

## Findings

- **Source:** kieran-python-reviewer, architecture-strategist
- **File:** `pyproject.toml`

## Proposed Solutions

### Option A: Pin to current major version (Recommended)
```toml
"fastmcp>=2.0,<3.0"
```
- **Effort:** Small (1 character change)
- **Risk:** None — can widen when 3.x compatibility is verified

## Acceptance Criteria

- [ ] Version constraint tightened to `<3.0`

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-28 | Created from review | Defensive dependency management |
