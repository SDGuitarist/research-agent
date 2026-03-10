---
status: resolved
priority: p2
issue_id: "120"
tags: [code-review, security, ci, supply-chain]
dependencies: []
unblocks: []
sub_priority: 2
---

# CI Actions Pinned to Mutable Major Version Tags

## Problem Statement

`.github/workflows/mcp-lint.yml` uses `actions/checkout@v4` and `actions/setup-python@v5` — mutable major-version tags. A compromised or hijacked tag could point to arbitrary code.

**Found by:** Security Sentinel

## Findings

- SHA pinning eliminates the mutable tag vector entirely
- Real-world attack: `tj-actions/changed-files` March 2025 incident
- Both actions are first-party (GitHub-maintained), which reduces but does not eliminate the risk

## Proposed Solutions

### Option A: Pin to full commit SHAs with version comments (Recommended)

```yaml
- uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2
- uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065  # v5.6.0
```

- **Pros:** Eliminates mutable tag risk, version comment preserves readability
- **Cons:** Requires manual or Dependabot-managed updates
- **Effort:** Small
- **Risk:** None

## Technical Details

- **Affected files:** `.github/workflows/mcp-lint.yml`

## Acceptance Criteria

- [ ] Both actions pinned to full commit SHAs
- [ ] Version comments present for readability
- [ ] CI still passes
