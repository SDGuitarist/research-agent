---
status: done
triage_reason: "Accepted — string priority causes TypeError during comparison"
priority: p3
issue_id: "017"
tags: [code-review, quality, validation]
dependencies: []
---

# YAML priority field not validated as int

## Problem Statement

`schema.py:99` uses `raw.get("priority", 3)` but doesn't validate the type. YAML could parse `priority: "high"` as a string, causing `TypeError` during comparison.

## Proposed Solutions

Add type check in `_parse_gap`:
```python
priority = raw.get("priority", 3)
if not isinstance(priority, int):
    raise SchemaError(f"Gap '{raw['id']}' has non-integer priority: {priority!r}")
```
- **Effort**: Small | **Risk**: Low

## Acceptance Criteria

- [ ] Non-integer priority raises SchemaError
- [ ] All tests pass
