---
status: ready
triage_reason: "Accepted — inconsistent with tuple convention for Gap sequences"
priority: p3
issue_id: "015"
tags: [code-review, quality, convention]
dependencies: []
---

# detect_stale returns list instead of tuple

## Problem Statement

`staleness.py:15` returns `list[Gap]` but convention is to use `tuple[Gap, ...]` for immutable sequences of Gap objects (e.g., `SchemaResult.gaps`, `select_batch` return).

## Proposed Solutions

Change return type to `tuple[Gap, ...]`.
- **Effort**: Small | **Risk**: Low

## Acceptance Criteria

- [ ] `detect_stale` returns `tuple[Gap, ...]`
- [ ] All tests pass
