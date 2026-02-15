---
status: pending
priority: p2
issue_id: "024"
tags: [code-review, security, prompt-injection]
dependencies: []
---

# Incomplete Sanitization — Missing & Escaping

## Problem Statement

`sanitize.py` only escapes `<` and `>` but not `&`. Content containing `&lt;` will not be double-escaped, creating potential entity injection confusion. The `&` must be escaped first.

## Findings

- **Source:** Security Sentinel agent
- **Location:** `research_agent/sanitize.py:4-11`

## Proposed Solutions

### Option A: Add & escaping (Recommended)
```python
def sanitize_content(text: str) -> str:
    return (text
        .replace("&", "&amp;")  # Must be first
        .replace("<", "&lt;")
        .replace(">", "&gt;"))
```
- **Effort:** Small (15 min)

## Acceptance Criteria

- [ ] `&` is escaped before `<` and `>`
- [ ] Existing sanitize tests updated
- [ ] No double-encoding of already-escaped entities
