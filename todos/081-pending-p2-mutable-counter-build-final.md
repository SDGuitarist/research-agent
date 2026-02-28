---
status: pending
priority: p2
issue_id: "081"
tags: [code-review, quality, python]
dependencies: []
unblocks: []
sub_priority: 5
---

# P2: Replace mutable counter in `_build_final_sections` with enumerate

## Problem Statement

`_build_final_sections()` in `synthesize.py` uses manual `n += 1` counter increments to number sections. This is error-prone when adding or removing conditional sections (Adversarial Analysis is conditional on `has_skeptic`).

## Findings

- Flagged by: kieran-python-reviewer (P2-4)

## Proposed Solutions

### Option A: Build list then enumerate (Recommended)

```python
sections = list(template.final_sections)
if has_skeptic:
    sections.append(("Adversarial Analysis", "Synthesize the skeptic review findings."))
sections.append(("Limitations & Gaps", "What sources don't cover, confidence levels."))
parts = [f"{i}. **{h}** — {d}" for i, (h, d) in enumerate(sections, draft_count + 1)]
parts.append("## Sources — All referenced URLs with [Source N] notation.")
```

- **Pros:** Eliminates mutation, impossible to forget an increment
- **Cons:** Creates an intermediate list
- **Effort:** Small (5 lines replaced)
- **Risk:** Low

## Technical Details

**Affected files:**
- `research_agent/synthesize.py` lines 114-126

## Acceptance Criteria

- [ ] Section numbering is identical before and after change
- [ ] Existing tests still pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-27 | Created from code review | Flagged by Python Reviewer |
