---
status: done
priority: p1
issue_id: "043"
tags: [code-review, architecture, performance]
dependencies: []
---

# P1: Quick mode can trigger coverage gap retry — no guard

## Problem Statement

`_evaluate_and_synthesize()` in `agent.py:522-528` triggers coverage gap retry for `insufficient_data` and `short_report` decisions **regardless of mode**. Quick mode is designed for speed (~$0.12, 4 sources), but a coverage retry adds ~2 seconds and ~$0.01 per under-delivering query via an extra Claude API call + potential search/fetch/summarize.

Every other expensive operation in the pipeline has a quick-mode bypass:
- Decomposition: `decompose=False` in quick mode config
- Critique: `if self.mode.is_quick: return`
- Skeptic: quick mode skips entirely

Coverage retry has no such guard.

## Findings

- Flagged by: security-sentinel, performance-oracle, architecture-strategist, kieran-python-reviewer
- No test exists asserting quick mode does NOT call `_try_coverage_retry`
- The cost overhead is proportionally large for quick mode (retry could double its source count)

## Proposed Solutions

### Option A: Add `is_quick` guard (Recommended)
Add `not self.mode.is_quick and` before the retry trigger condition.
- Pros: Simple, matches existing patterns, 1 line change
- Cons: None
- Effort: Small
- Risk: None

### Option B: Add `retry_on_gaps: bool` field to `ResearchMode`
Like the `decompose: bool` field, make this configurable per mode.
- Pros: More flexible, follows the frozen-dataclass convention
- Cons: Over-engineering for a boolean that only differs for quick
- Effort: Small-Medium
- Risk: Low

## Recommended Action

Option A.

## Technical Details

- **File:** `research_agent/agent.py:522-528`
- **Also add test:** `tests/test_agent.py` — test that quick mode with `insufficient_data` does NOT call `_try_coverage_retry`

## Acceptance Criteria

- [ ] `_evaluate_and_synthesize` skips coverage retry when `self.mode.is_quick`
- [ ] Test confirms quick mode with `insufficient_data` decision does not call `_try_coverage_retry`
- [ ] All 693 tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-25 | Created from review | Flagged by 4 of 6 review agents |

## Resources

- `research_agent/agent.py:522-528` — retry trigger
- `research_agent/agent.py:150-151` — quick mode critique guard (pattern to follow)
