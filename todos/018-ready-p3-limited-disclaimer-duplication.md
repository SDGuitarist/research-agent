---
status: ready
triage_reason: "Accepted — disclaimer template duplicated in two functions"
priority: p3
issue_id: "018"
tags: [code-review, quality, duplication]
dependencies: []
---

# Limited sources disclaimer duplicated

## Problem Statement

The limited sources disclaimer string template is duplicated in `synthesize_report` (lines 109-114) and `synthesize_final` (lines 445-449).

## Proposed Solutions

Extract to `_build_limited_disclaimer(total_count, dropped_count) -> str`.
- **Effort**: Small | **Risk**: Low

## Acceptance Criteria

- [ ] Disclaimer logic exists in one place
- [ ] All tests pass
