---
status: complete
triage_reason: "Accepted — symlink validation missing on atomic write target"
priority: p2
issue_id: "012"
tags: [code-review, security]
dependencies: []
---

# Symlink race in safe_io.py atomic_write

## Problem Statement

`safe_io.py:28-40` performs no symlink validation on the target path. `os.rename(tmp_path, target)` follows symlinks, so if a symlink is created at the target location, writes could be redirected.

## Findings

- **Security sentinel**: Medium severity. Low exploitability in single-user CLI context.

**File:** `research_agent/safe_io.py:28-40`

## Proposed Solutions

### Option A: Add resolve() and symlink check (Recommended)
```python
target = Path(path).resolve()
if target.is_symlink():
    raise StateError(f"Refusing to write through symlink: {path}")
```
- **Effort**: Small | **Risk**: Low

### Option B: Replace safe_io.py with Path.write_text()
Simplicity reviewer argues atomic writes are overkill for a CLI tool.
- **Effort**: Small | **Risk**: Low

## Acceptance Criteria

- [ ] `atomic_write` resolves symlinks before writing
- [ ] All tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-15 | Created from code review | Security sentinel flagged |
