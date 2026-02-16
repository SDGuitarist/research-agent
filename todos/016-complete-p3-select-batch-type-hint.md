---
status: complete
triage_reason: "Accepted — Sequence[Gap] is more Pythonic than union type"
priority: p3
issue_id: "016"
tags: [code-review, quality, types]
dependencies: []
---

# select_batch accepts tuple|list instead of Sequence

## Problem Statement

`staleness.py:62` accepts `tuple[Gap, ...] | list[Gap]` instead of the Pythonic `Sequence[Gap]`.

## Proposed Solutions

Use `from collections.abc import Sequence` and accept `Sequence[Gap]`.
- **Effort**: Small | **Risk**: Low

## Acceptance Criteria

- [ ] `select_batch` parameter uses `Sequence[Gap]`
- [ ] All tests pass
