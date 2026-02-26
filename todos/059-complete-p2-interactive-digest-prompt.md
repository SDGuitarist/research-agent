---
status: complete
priority: p2
issue_id: "059"
tags: [code-review, agent-native]
dependencies: []
---

# P2: Digest "mark as reviewed" prompt assumes interactive session

## Problem Statement

The digest skill says "Ask the user: 'Mark all N items as reviewed?'" — this blocks in automated/agent contexts where there is no interactive user to respond.

**Location:** `.claude/skills/research-digest.md` lines 67-71 (Step 4)

## Findings

- **agent-native-reviewer**: WARNING. An outer orchestrating agent calling `/research:digest` as a sub-step would stall at the review prompt.

## Proposed Solutions

### Option A: Add auto-review convention (Recommended)
Add a sentence: "If the user passed 'auto' as an argument, or if running in a non-interactive context, mark all items as reviewed automatically without asking."
- **Pros:** Simple, backwards-compatible, enables automation
- **Cons:** Skill argument handling is informal (Claude interprets it)
- **Effort:** Small
- **Risk:** Low

## Recommended Action

Option A — add auto-review mode.

## Technical Details

- **Affected files:** `.claude/skills/research-digest.md`
- **Components:** Step 4 (Mark as Reviewed)

## Acceptance Criteria

- [ ] Digest skill can run non-interactively when passed "auto" argument
- [ ] Interactive mode still asks by default

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-26 | Created from code review | agent-native-reviewer finding |

## Resources

- PR: feat/background-research-agents
