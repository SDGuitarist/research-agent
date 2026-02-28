---
status: done
priority: p2
issue_id: "077"
tags: [code-review, security, sanitization]
dependencies: ["075"]
unblocks: []
sub_priority: 1
---

# P2: Template field values flow unsanitized into LLM prompts

## Problem Statement

Template fields (`heading`, `description`, `context_usage`) extracted from YAML frontmatter are injected directly into LLM prompt strings in `synthesize.py` without passing through `sanitize_content()`. If a context file were tampered with, these fields could inject arbitrary instructions into the LLM prompt, potentially breaking out of XML boundaries.

Exploitability is low (requires filesystem write access), but this violates the project's established "sanitize at the data boundary" pattern documented in `docs/solutions/security/non-idempotent-sanitization-double-encode.md`.

## Findings

- Flagged by: security-sentinel (Finding 1 + Finding 4, Medium severity)
- Confirmed by: learnings-researcher (sanitization boundary pattern)
- Unsanitized locations: `synthesize.py` lines 92, 117-119, 220-224, 497-498
- The body content IS sanitized at `context.py:186`, but template fields bypass this

## Proposed Solutions

### Option A: Sanitize in `_parse_template()` after YAML parsing (Recommended)

Apply `sanitize_content()` to each field value after YAML parsing but before storing in `ReportTemplate`:

```python
draft_sections = tuple(
    (sanitize_content(h), sanitize_content(d))
    for h, d in _parse_sections(draft_raw)
)
final_sections = tuple(
    (sanitize_content(h), sanitize_content(d))
    for h, d in _parse_sections(final_raw)
)
context_usage = sanitize_content(tmpl.get("context_usage", ""))
name = sanitize_content(name)
```

- **Pros:** Single sanitization point, all downstream consumers are protected
- **Cons:** `sanitize_content()` escapes `&` and `<` — section headings with these chars will be escaped in prompts. Unlikely but possible.
- **Effort:** Small (6 line changes in `_parse_template`)
- **Risk:** Low — template field values are short strings, sanitization won't corrupt them

### Option B: Sanitize at each consumption site in `synthesize.py`

- **Pros:** Only sanitizes when entering a prompt
- **Cons:** Multiple sites to update, easy to miss one
- **Effort:** Medium

## Technical Details

**Affected files:**
- `research_agent/context.py` — `_parse_template()` (add sanitization)
- `research_agent/synthesize.py` — consumption sites (no changes needed with Option A)

## Acceptance Criteria

- [ ] All template field values pass through `sanitize_content()` before reaching any LLM prompt
- [ ] Test added: template fields with `<` or `&` are escaped in the stored `ReportTemplate`
- [ ] Existing tests still pass (may need updates for escaped content)

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-27 | Created from code review | Flagged by Security Sentinel, confirmed by Learnings Researcher |
