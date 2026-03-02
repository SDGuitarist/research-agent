---
status: complete
priority: p3
issue_id: "113"
tags: [code-review, performance, cost]
dependencies: []
unblocks: []
sub_priority: 5
---

# Cap iteration_max_tokens to prevent bloated deep-mode sections

## Problem Statement

`iteration_max_tokens = self.mode.max_tokens // 5` gives 1600 for deep mode — allowing ~800 word mini-reports when the target is ~300 words. This wastes output tokens and risks diluting the main report with overly long appendices.

## Findings

- **performance-oracle**: P3 — cap at 800 for consistency

**Location:** `research_agent/agent.py:308`

## Proposed Solutions

### Option A: Add upper bound cap (Recommended)
```python
iteration_max_tokens = min(self.mode.max_tokens // 5, 800)
```

- **Effort:** Trivial (1 line change)
- **Risk:** None

## Acceptance Criteria

- [ ] `iteration_max_tokens` capped at a reasonable maximum (~800)
- [ ] Deep mode produces concise supplementary sections
