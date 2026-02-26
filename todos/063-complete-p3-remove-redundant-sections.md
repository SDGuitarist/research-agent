---
status: complete
priority: p3
issue_id: "063"
tags: [code-review, simplicity]
dependencies: []
---

# P3: Remove redundant sections from skill files

## Problem Statement

Several sections in the skill files are redundant or over-specified for v1:
1. "How It Works" section (lines 11-19 of research-queue.md) — restates Steps 1-7
2. Report preview in completion notification (line 137-138) — digest serves this purpose
3. Digest Step 5 spend summary (lines 75-80 of research-digest.md) — redundant with digest content
4. Sub-agent conditional in digest (lines 27-36) — premature optimization, always read directly for v1

**Location:** Multiple locations in both skill files

## Findings

- **code-simplicity-reviewer**: ~25 lines removable across both files with zero functionality loss.

## Proposed Solutions

### Option A: Remove all four redundancies (Recommended)
- Delete "How It Works" section
- Remove report preview from notification (just show query + path + cost)
- Remove Step 5 from digest (add total cost line to Step 3 output instead)
- Remove sub-agent conditional (always read directly)
- **Effort:** Small
- **Risk:** Low

## Acceptance Criteria

- [ ] Redundant sections removed
- [ ] All functionality preserved
- [ ] Skills are shorter and clearer for Claude to interpret

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-26 | Created from code review | simplicity-reviewer findings |
