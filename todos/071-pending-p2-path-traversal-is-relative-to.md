---
status: done
priority: p2
issue_id: "071"
tags: [code-review, security]
dependencies: []
---

# P2: Path traversal defense — use `is_relative_to` instead of string prefix

## Problem Statement

`resolve_context_path()` defense layer 2 uses `str(path).startswith(str(contexts_resolved) + "/")`. Python 3.9+ provides `Path.is_relative_to()` which handles edge cases (case-insensitive filesystems, symlinks). Layer 1 blocks all realistic attacks, so this is hardening.

## Findings

- Flagged by: kieran-python-reviewer (P1), pattern-recognition-specialist (P2), data-integrity-guardian (P3)
- 3 agents flagged independently
- Refinement of todo 054 (which implemented the current fix)
- The digest skill's own SKILL.md recommends `is_relative_to` — inconsistent with Python code

## Fix

```python
# Replace in context.py:54-58:
if not path.is_relative_to(contexts_resolved):
    raise ValueError(...)
```

## Acceptance Criteria

- [ ] Uses `Path.is_relative_to()` instead of string prefix
- [ ] All existing path traversal tests still pass

## Technical Details

- **Affected files:** `research_agent/context.py`
- **Effort:** Tiny (1 line)
