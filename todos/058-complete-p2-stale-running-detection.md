---
status: complete
priority: p2
issue_id: "058"
tags: [code-review, architecture]
dependencies: []
---

# P2: Stale Running detection can't distinguish dead sessions from active ones

## Problem Statement

Step 2 unconditionally moves all `## Running` items back to `## Queued`. If the user runs `/research:queue` while background agents from the same session are still active, the skill re-queues items that are actively running — causing double-launches and double budget charges.

**Location:** `.claude/skills/research-queue.md` lines 48-52 (Step 2)

## Findings

- **architecture-strategist**: MEDIUM severity. The plan's feed-forward explicitly flagged this as "least confident" area.
- **code-simplicity-reviewer**: Suggested replacing auto-recovery with a user warning for v1 (simpler and safer).

## Proposed Solutions

### Option A: Replace with user warning (Recommended for v1)
Instead of auto-recovering, warn the user: "Found N items in Running. Move them back to Queued if you want to retry." Then only process `## Queued` items.
- **Pros:** Simplest, safest, avoids double-launches
- **Cons:** Requires manual intervention for crashed sessions
- **Effort:** Small
- **Risk:** Low

### Option B: Add age-based guard
Record a timestamp in Running lines. Only re-queue items older than 15 minutes.
- **Pros:** Handles both cases (stale and active)
- **Cons:** More complex, adds timestamp parsing requirement
- **Effort:** Medium
- **Risk:** Medium (Claude must parse timestamps correctly)

## Recommended Action

Option A for v1 — warn instead of auto-recover. Revisit with Option B if it becomes a friction point.

## Technical Details

- **Affected files:** `.claude/skills/research-queue.md`
- **Components:** Step 2 (Handle Stale Running Items)

## Acceptance Criteria

- [ ] Running items are NOT automatically moved back to Queued
- [ ] User is warned about Running items and told how to re-queue manually
- [ ] Double-launch scenario is eliminated

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-26 | Created from code review | architecture-strategist + simplicity-reviewer findings |

## Resources

- PR: feat/background-research-agents
- Plan feed-forward: "Stale Running item detection... This heuristic may be fragile."
