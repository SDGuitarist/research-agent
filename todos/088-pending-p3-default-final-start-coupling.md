---
status: pending
priority: p3
issue_id: "088"
tags: [code-review, architecture, maintainability]
dependencies: []
unblocks: []
sub_priority: 2
---

# P3: `_DEFAULT_FINAL_START = 5` implicit coupling to draft sections

## Problem Statement

`_DEFAULT_FINAL_START = 5` in `synthesize.py` line 127 is a magic constant whose value is derived from counting the 4 generic draft sections defined 235 lines below in `synthesize_draft`'s else-branch. If someone adds or removes a generic draft section, this constant silently produces wrong section numbering. The comment documents the assumption but there is no enforcement.

## Findings

- Flagged by: kieran-python-reviewer (P3), code-simplicity-reviewer (P3), architecture-strategist (P3), pattern-recognition-specialist (P3)
- 4/6 agents flagged this — strong consensus but all agreed P3 severity
- The template-driven path (`_build_final_sections`) correctly derives numbering from `draft_count` parameter
- Only the generic (non-template) fallback path uses the hardcoded constant
- Risk is low: generic draft sections haven't changed, and the comment makes the coupling discoverable

## Proposed Solutions

### Option A: Extract generic draft sections into a tuple constant
- Create `_DEFAULT_DRAFT_SECTIONS` tuple at module level
- Derive `_DEFAULT_FINAL_START = len(_DEFAULT_DRAFT_SECTIONS) + 1`
- Use the tuple in `synthesize_draft` as well
- **Pros:** Single source of truth, coupling enforced by code
- **Cons:** Larger change, touches synthesize_draft prompt construction
- **Effort:** Medium
- **Risk:** Low

### Option B: Add a test assertion (Minimal)
- Add a test that asserts `_DEFAULT_FINAL_START == 5` with a comment to update if draft sections change
- **Pros:** Documents the assumption explicitly
- **Cons:** Still requires manual update
- **Effort:** Small
- **Risk:** None

### Option C: Leave as-is (Acceptable)
- The comment documents the assumption
- Generic path is a stable fallback
- **Effort:** None

## Technical Details

**Affected files:**
- `research_agent/synthesize.py` line 127 (constant), lines 362-376 (draft sections)

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-28 | Created from P2 triage review | 4/6 agents flagged; all agreed low severity |
