---
status: pending
priority: p1
issue_id: "076"
tags: [code-review, logic-error, parsing]
dependencies: []
unblocks: []
sub_priority: 2
---

# P1: YAML frontmatter delimiter `find("---", 3)` edge case

## Problem Statement

In `context.py:_parse_template()` line 57, `stripped.find("---", 3)` searches for the closing `---` starting at character index 3. This has two edge cases:

1. If YAML content contains `---` (valid YAML document separator), the parser splits on the wrong delimiter.
2. `---\n---\n` (empty frontmatter) finds the closing `---` immediately — this case is handled by the `not isinstance(data, dict)` check, but only accidentally.

The safer pattern is to search for `\n---` (newline before closing delimiter) which matches how standard frontmatter parsers work.

## Findings

- Flagged by: kieran-python-reviewer (P1-1)
- Low probability in practice (author-controlled files), but silent misparsing is worse than a crash
- The fix is a one-line change

## Proposed Solutions

### Option A: Search for `\n---` instead of `---` (Recommended)

```python
end = stripped.find("\n---", 3)
if end == -1:
    return (raw, None)
yaml_block = stripped[3:end]
body = stripped[end + 4:].lstrip("\n")  # +4 for \n---
```

- **Pros:** Matches standard frontmatter parsing convention, handles embedded `---` in YAML
- **Cons:** Slightly changes the offset math
- **Effort:** Small (2 line changes)
- **Risk:** Low — add test for YAML containing `---`

### Option B: Use a regex for frontmatter extraction

```python
import re
match = re.match(r'^---\n(.*?)\n---\n?(.*)', stripped, re.DOTALL)
```

- **Pros:** More robust, handles all edge cases
- **Cons:** Adds regex complexity, overkill for the problem
- **Effort:** Small
- **Risk:** Low

## Technical Details

**Affected files:**
- `research_agent/context.py` line 57

## Acceptance Criteria

- [ ] `_parse_template()` correctly handles YAML containing `---` inside
- [ ] Empty frontmatter (`---\n---\n`) returns `(body, None)` not a parse error
- [ ] Test added: YAML with embedded `---` parses correctly
- [ ] Existing tests still pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-27 | Created from code review | Flagged by Python Reviewer |
