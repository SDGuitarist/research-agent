---
status: complete
priority: p3
issue_id: "110"
tags: [code-review, quality, patterns]
dependencies: []
unblocks: []
sub_priority: 2
---

# Missing named constants for validation thresholds in iterate.py

## Problem Statement

`iterate.py` hardcodes validation thresholds inline (`min_words=3`, `max_words=10`, `max_reference_overlap=0.6`, etc.) whereas `decompose.py` and `coverage.py` extract these into module-level named constants. This is inconsistent.

## Findings

- **pattern-recognition-specialist**: P3 — inconsistent with established pattern

**Location:** `research_agent/iterate.py:122-131, 246-254`

## Proposed Solutions

### Option A: Extract to module-level constants (Recommended)
```python
MIN_REFINED_WORDS = 3
MAX_REFINED_WORDS = 10
MAX_REFINED_OVERLAP = 0.6
MIN_FOLLOWUP_WORDS = 4
MAX_FOLLOWUP_WORDS = 15
MAX_FOLLOWUP_OVERLAP = 0.5
```

- **Effort:** Small
- **Risk:** None

## Acceptance Criteria

- [ ] Validation thresholds extracted to named constants
- [ ] Constants used in `validate_query_list()` calls
