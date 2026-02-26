---
status: complete
priority: p2
issue_id: "057"
tags: [code-review, security]
dependencies: []
---

# P2: Path traversal via report paths in queue file

## Problem Statement

Both skills read report file paths from `reports/queue.md` completed entries and pass them to the Read tool. Since the queue file is hand-editable, a malformed entry could contain a traversal path like `../../../.env`, causing the skill to read arbitrary files.

**Location:** `.claude/skills/research-digest.md` Step 2 (lines 25-37), `.claude/skills/research-queue.md` Step 7 (lines 137-138)

## Findings

- **security-sentinel**: MEDIUM severity. Single-user context limits impact (user already has file access), but violates principle of least privilege. Risk increases if queue file is ever shared.

## Proposed Solutions

### Option A: Add path validation instructions (Recommended)
Before reading a report file, validate the path: must start with `reports/`, must not contain `..`, must end with `.md`.
- **Pros:** Simple, defensive, covers both skills
- **Cons:** Adds 2-3 lines of instructions per skill
- **Effort:** Small
- **Risk:** Low

## Recommended Action

Option A — add path validation.

## Technical Details

- **Affected files:** `.claude/skills/research-queue.md`, `.claude/skills/research-digest.md`

## Acceptance Criteria

- [ ] Report paths are validated before reading
- [ ] Paths containing `..` are rejected with a warning
- [ ] Only paths under `reports/` are accepted

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-26 | Created from code review | security-sentinel finding |

## Resources

- PR: feat/background-research-agents
