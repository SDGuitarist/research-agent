---
status: complete
priority: p2
issue_id: "060"
tags: [code-review, architecture, simplicity]
dependencies: []
---

# P2: daily_spend.json is over-engineered — flatten to 3 fields

## Problem Statement

The JSON schema stores a full `queries` array with per-query objects (query, mode, estimated_cost, status, report_path, timestamp). This duplicates information already tracked in `reports/queue.md`. The only thing the spend file needs to answer is "how much have I spent today?" — that requires 3 fields, not an unbounded array.

**Location:** `.claude/skills/research-queue.md` lines 56-67 (Step 3), lines 93 and 135-136 (JSON updates)

## Findings

- **code-simplicity-reviewer**: MEDIUM severity. Biggest YAGNI violation. Removes ~15 lines of JSON management instructions.
- **architecture-strategist**: LOW. Noted budget source-of-truth split between queue.md and JSON. Simplifying JSON to just a counter resolves this.

## Proposed Solutions

### Option A: Flatten to 3 fields (Recommended)
```json
{"date": "2026-02-25", "budget": 5.00, "total_spent": 0.47}
```
Remove the `queries` array entirely. Queue file is already the source of truth for query state.
- **Pros:** Eliminates ~15 lines of "add entry" / "update status" instructions, simpler for Claude to manage
- **Cons:** Loses per-query spend breakdown in JSON (still visible in queue file)
- **Effort:** Small
- **Risk:** Low

## Recommended Action

Option A — flatten the schema.

## Technical Details

- **Affected files:** `.claude/skills/research-queue.md`
- **Components:** Steps 3, 5, 7 (all spend JSON interactions)

## Acceptance Criteria

- [ ] daily_spend.json has only `date`, `budget`, `total_spent`
- [ ] No per-query tracking in JSON (queue file handles this)
- [ ] Budget check still works correctly (remaining = budget - total_spent)

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-26 | Created from code review | simplicity-reviewer + architecture-strategist findings |

## Resources

- PR: feat/background-research-agents
