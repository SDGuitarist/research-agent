---
status: complete
priority: p2
issue_id: "056"
tags: [code-review, architecture, agent-native]
dependencies: []
---

# P2: Hardcoded absolute path breaks portability

## Problem Statement

The skill contains `cd /Users/alejandroguillen/Projects/research-agent` in the background agent launch command. This is machine-specific and will break if the project is moved, cloned elsewhere, or used by another developer.

**Location:** `.claude/skills/research-queue.md` line 99 (Step 5, item 4)

## Findings

- **agent-native-reviewer**: MEDIUM severity. Only issue that would cause a hard failure on a different machine.
- **security-sentinel**: Noted as non-security observation. Not a credential, but limits portability.
- Background Task agents inherit the working directory from the parent session, so the `cd` may be unnecessary entirely.

## Proposed Solutions

### Option A: Remove the `cd` command entirely (Recommended)
Background Task agents already start in the project directory. The `cd` is redundant.
- **Pros:** Simplest, most portable, zero maintenance
- **Cons:** Relies on Task agent working directory behavior (which is documented)
- **Effort:** Small
- **Risk:** Low

### Option B: Use `$(pwd)` in the command
Replace hardcoded path with `cd $(pwd)`.
- **Pros:** Always resolves to current directory
- **Cons:** Still adds unnecessary complexity if agents inherit cwd
- **Effort:** Small
- **Risk:** Low

## Recommended Action

Option A — remove the `cd` command.

## Technical Details

- **Affected files:** `.claude/skills/research-queue.md`
- **Components:** Step 5 (background agent launch template)

## Acceptance Criteria

- [ ] No hardcoded absolute paths in skill files
- [ ] Background agents still find and run `python3 main.py` correctly

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-26 | Created from code review | agent-native-reviewer + security-sentinel findings |

## Resources

- PR: feat/background-research-agents
