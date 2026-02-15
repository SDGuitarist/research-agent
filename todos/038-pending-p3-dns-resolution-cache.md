---
status: pending
priority: p3
issue_id: "038"
tags: [code-review, performance]
dependencies: []
---

# Per-Run DNS Resolution Cache

## Problem Statement

`_resolve_and_validate_host()` in `fetch.py` resolves DNS for every URL independently. Adding a per-run cache for repeated domains would save 50-300ms across a typical research run.

## Findings

- **Source:** Performance Oracle agent
- **Location:** `research_agent/fetch.py:104-131`

## Proposed Solutions

### Option A: Simple dict cache (Recommended)
Cache `{hostname: resolved_ips}` for the duration of the run. Clear on each new research invocation.
- **Effort:** Small (30 min)

## Acceptance Criteria

- [ ] Repeated DNS lookups for same hostname use cache
- [ ] Cache scoped to single run (not persistent)
- [ ] All tests pass
