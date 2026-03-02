---
status: complete
priority: p2
issue_id: "108"
tags: [code-review, performance, cost]
dependencies: []
unblocks: []
sub_priority: 7
---

# Full draft sent to refined query generation — truncate to save tokens

## Problem Statement

`generate_refined_queries()` sanitizes and sends the entire draft report to the LLM. In deep mode this can be 30,000+ characters (~5-8K input tokens). The LLM only needs enough context to identify gaps — `generate_followup_questions()` already truncates to 2000 chars.

## Findings

- **performance-oracle**: Saves ~$0.005-0.01/call + ~0.5-1s latency

**Location:** `research_agent/iterate.py:61`

## Proposed Solutions

### Option A: Truncate draft before sanitizing (Recommended)
```python
safe_draft = sanitize_content(draft[:3000])  # ~750 tokens
```

- **Pros:** Reduces input tokens by 60-80%, faster API response
- **Cons:** May miss gaps in the last portion of long reports
- **Effort:** Trivial (1 line)
- **Risk:** Low — 3000 chars is enough for gap diagnosis

## Acceptance Criteria

- [ ] Draft truncated before sanitization in `generate_refined_queries()`
- [ ] Truncation limit appropriate for gap analysis (~3000 chars)
