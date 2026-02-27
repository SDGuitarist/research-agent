---
status: done
priority: p3
issue_id: "061"
tags: [code-review, performance]
dependencies: []
---

# P3: list_available_contexts() reads entire files for 5-line previews

## Problem Statement

`list_available_contexts()` in `context.py:108-111` calls `path.read_text().strip()` to read entire files, then discards everything after the first 5 lines. Currently harmless with one 244-line file (~17KB), but wastes I/O proportional to file size rather than preview size.

## Findings

- Flagged by: performance-oracle (LOW-MEDIUM)
- Current file (pfe.md) is 244 lines — reads 244 lines to keep 5
- Fix is trivial: read line-by-line and stop after 5

## Proposed Solutions

### Option A: Line-by-line read (Recommended)
```python
lines = []
with path.open() as f:
    for i, line in enumerate(f):
        if i >= _PREVIEW_LINES:
            break
        lines.append(line.rstrip())
preview = "\n".join(lines)
```
- Pros: O(_PREVIEW_LINES) instead of O(file_size), trivial change
- Effort: Small (6 lines)
- Risk: Low

## Technical Details

- **Affected files:** `research_agent/context.py`

## Acceptance Criteria

- [ ] `list_available_contexts()` returns same previews as before
- [ ] No full-file read for preview generation

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-26 | Created from code review | |
