---
status: resolved
priority: p2
issue_id: "121"
tags: [code-review, performance, ci]
dependencies: []
unblocks: []
sub_priority: 3
---

# CI Workflow Missing pip Cache

## Problem Statement

`.github/workflows/mcp-lint.yml` runs `pip install -e .` on every invocation without caching. The project has 10 dependencies including C-extension packages (`lxml`, `trafilatura`), costing 30-60 seconds per run.

**Found by:** Performance Oracle

## Findings

- `actions/setup-python@v5` supports built-in pip caching via `cache: 'pip'`
- Expected savings: 20-40 seconds per run after the first
- Every push to main and every PR pays the full install time

## Proposed Solutions

### Option A: Add pip cache to setup-python (Recommended)

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
    cache: 'pip'
```

- **Pros:** One-line addition, 20-40s savings per run
- **Cons:** None
- **Effort:** Small
- **Risk:** None

## Technical Details

- **Affected files:** `.github/workflows/mcp-lint.yml`

## Acceptance Criteria

- [ ] `cache: 'pip'` added to setup-python step
- [ ] CI still passes
