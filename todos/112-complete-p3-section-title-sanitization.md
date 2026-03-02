---
status: complete
priority: p3
issue_id: "112"
tags: [code-review, security, consistency]
dependencies: ["102"]
unblocks: []
sub_priority: 4
---

# Unsanitized section_title in mini-report markdown output

## Problem Statement

The `section_title` in `synthesize_mini_report()` is constructed from LLM-generated query text that has passed through `validate_query_list()` but not `sanitize_content()`. The title ends up in the final markdown heading. Risk is very low (markdown heading, not LLM input) but inconsistent with the three-layer defense pattern.

## Findings

- **security-sentinel**: LOW — consistency fix for defense-in-depth

**Location:** `research_agent/agent.py:312-315`

## Proposed Solutions

### Option A: Sanitize query text before building title
```python
safe_q = sanitize_content(q)
title = f"Deeper Dive: {safe_q}" if q in refined_result.items else f"Follow-Up: {safe_q}"
```

- **Effort:** Trivial
- **Risk:** None

## Acceptance Criteria

- [ ] Query text sanitized before inclusion in section title
