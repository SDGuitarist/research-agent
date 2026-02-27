---
status: done
priority: p1
issue_id: "065"
tags: [code-review, data-integrity, security]
dependencies: []
---

# P1: Double-sanitization produces `&amp;amp;` in reports

## Problem Statement

Context content goes through `sanitize_content()` at each consumer (`synthesize_draft` and `synthesize_final`). Since `sanitize_content()` replaces `&` with `&amp;`, double-sanitization produces `&amp;amp;`. Any `&` in context files (e.g., "R&D") appears corrupted in deep mode reports.

## Findings

- Flagged by: performance-oracle (P2 redundant work), security-sentinel (P1 architectural)
- `sanitize_content()` is not idempotent — this is the root cause
- Deep mode calls both `synthesize_draft()` and `synthesize_final()`, each sanitizing the same context
- Combined with finding: sanitization should happen at load boundary, not per-consumer

## Fix

Sanitize context content once at load time in `load_full_context()`:
```python
# context.py, in load_full_context():
content = sanitize_content(path.read_text().strip())
```

Then remove redundant `sanitize_content(context)` calls in:
- `synthesize.py:132` (synthesize_draft)
- `synthesize.py:441` (synthesize_final)
- `decompose.py:92`
- `skeptic.py:42-47` (already has _build_context_block helper)

## Acceptance Criteria

- [ ] Context with `&` characters appears as `&` in final report (not `&amp;`)
- [ ] `sanitize_content` called exactly once per context load
- [ ] All redundant sanitize calls removed from consumers
- [ ] Tests verify no double-encoding

## Technical Details

- **Affected files:** `research_agent/context.py`, `synthesize.py`, `decompose.py`, `skeptic.py`, tests
- **Effort:** Medium (~20 lines across 4 files)
- **Risk:** Low — all consumers currently sanitize, removing is safe if load-time sanitization is added
