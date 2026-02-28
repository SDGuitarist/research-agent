---
status: done
priority: p1
issue_id: "075"
tags: [code-review, logic-error, synthesize]
dependencies: []
unblocks: []
sub_priority: 1
---

# P1: `body if body else raw` fallback leaks YAML syntax into prompts

## Problem Statement

In `context.py:_parse_template()`, when YAML frontmatter is valid but the file has no body after the closing `---`, the expression `body if body else raw` falls back to `raw` — which includes the full YAML frontmatter with `---` delimiters. This YAML syntax then flows through `sanitize_content()` and into LLM prompts as "context content."

This means a template-only context file (frontmatter with no body) would inject YAML template definitions into the research report prompt, confusing the LLM.

## Findings

- Flagged by: kieran-python-reviewer (P1-2)
- Confirmed by: architecture-strategist (risk 3 discussion)
- Appears at 3 locations: `context.py` lines 72, 100, 104
- The intent is clearly "return the body after frontmatter" but the fallback defeats this

## Proposed Solutions

### Option A: Return empty string when body is empty (Recommended)

Replace `body if body else raw` with just `body` in all 3 locations. If the file is all frontmatter with no body, the `body` will be empty string — `load_full_context` will then create `ContextResult.empty()` since `sanitize_content("")` returns `""`.

- **Pros:** Simple, consistent, no YAML leakage
- **Cons:** A template-only context file would have `template` but no `content` — need to verify this works downstream
- **Effort:** Small (3 line changes)
- **Risk:** Low — check that empty body + valid template still routes correctly through agent.py

### Option B: Return body, log warning when empty

Same as A but add a `logger.warning("Context file has template but no body content")` when body is empty.

- **Pros:** Alerts the author that the file has no content
- **Cons:** Slightly more code
- **Effort:** Small

## Technical Details

**Affected files:**
- `research_agent/context.py` lines 72, 100, 104

## Acceptance Criteria

- [ ] `_parse_template()` never returns `raw` when frontmatter was successfully parsed
- [ ] A context file with only YAML frontmatter (no body) returns `("", template)` not `(raw, None)`
- [ ] Test added: frontmatter-only file does not leak YAML into body
- [ ] Existing tests still pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-27 | Created from code review | Flagged by Python Reviewer |
