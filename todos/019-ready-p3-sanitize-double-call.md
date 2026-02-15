---
status: done
triage_reason: "Accepted — redundant sanitization of same input"
priority: p3
issue_id: "019"
tags: [code-review, quality]
dependencies: []
---

# sanitize_content double-called on business_context

## Problem Statement

`synthesize.py:377` sanitizes `business_context` for budget allocation, then `synthesize.py:401` sanitizes the original `business_context` again when building the prompt. Redundant work.

## Proposed Solutions

Sanitize once and reuse the sanitized version.
- **Effort**: Small | **Risk**: Low

## Acceptance Criteria

- [ ] `sanitize_content` called once per unique input
- [ ] All tests pass
