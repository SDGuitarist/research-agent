---
status: done
priority: p2
issue_id: "079"
tags: [code-review, validation, parsing]
dependencies: ["075"]
unblocks: []
sub_priority: 3
---

# P2: Validate non-empty sections in `_parse_template()`

## Problem Statement

A template with `draft: []` and `final: [{"Foo": "bar"}]` would create a `ReportTemplate` with `draft_sections=()`. Since `()` is falsy, `synthesize_draft` would fall back to the generic 4-section structure at line 346, while `synthesize_final` would use the template's final sections. This creates a mixed template/generic report — a subtle inconsistency.

## Findings

- Flagged by: architecture-strategist (Finding 3)
- Empty tuples are falsy in Python, so the fallback works accidentally
- No test covers the empty-sections case

## Proposed Solutions

### Option A: Reject templates with both sections empty (Recommended)

In `_parse_template()`, after parsing sections:

```python
if not draft_sections and not final_sections:
    logger.warning("Template has no sections defined — ignoring")
    return (body if body else raw, None)
```

- **Pros:** Prevents mixed template/generic behavior
- **Cons:** Rejects a template that has only `context_usage` but no sections
- **Effort:** Small (3 lines)
- **Risk:** Low

## Technical Details

**Affected files:**
- `research_agent/context.py` — `_parse_template()` (add validation)

## Acceptance Criteria

- [ ] Template with `draft: []` and `final: []` returns `None` template
- [ ] Template with `draft: []` and valid `final:` still returns a valid template (one empty is OK)
- [ ] Test added for empty sections case

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-27 | Created from code review | Flagged by Architecture Strategist |
