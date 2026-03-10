---
status: resolved
priority: p2
issue_id: "119"
tags: [code-review, security, ci]
dependencies: []
unblocks: []
sub_priority: 1
---

# CI Workflow Missing Explicit Permissions Block

## Problem Statement

`.github/workflows/mcp-lint.yml` does not declare a top-level `permissions` block. Workflows on `push` to `main` inherit the repository's default token permissions (typically `write` for all scopes). This violates the principle of least privilege.

**Found by:** Security Sentinel

## Findings

- The workflow only needs read access to check out code and run a lint script
- If a compromised dependency runs during `pip install -e .`, it would have write access to repository contents, packages, and other scopes
- Real-world precedent: `tj-actions/changed-files` incident (March 2025)

## Proposed Solutions

### Option A: Add top-level permissions block (Recommended)

Add between `on:` and `jobs:`:
```yaml
permissions:
  contents: read
```

- **Pros:** One-line fix, defense-in-depth
- **Cons:** None
- **Effort:** Small
- **Risk:** None

## Technical Details

- **Affected files:** `.github/workflows/mcp-lint.yml`

## Acceptance Criteria

- [ ] Workflow has explicit `permissions: contents: read`
- [ ] CI still passes
