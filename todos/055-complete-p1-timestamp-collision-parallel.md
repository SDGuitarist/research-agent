---
status: complete
priority: p1
issue_id: "055"
tags: [code-review, architecture]
dependencies: []
---

# P1: Timestamp collision when generating parallel output paths

## Problem Statement

The skill generates output paths with microsecond timestamps for parallel queries, but Claude generates all paths in a single message — it has no real clock. Real-world test data confirms both queries got **identical timestamps** (`005243522271`). Collision was avoided only because query slugs differed. Two similar queries truncated to the same 50-char prefix would overwrite each other.

**Location:** `.claude/skills/research-queue.md` lines 82-86 (Step 5, item 1)

## Findings

- **architecture-strategist**: HIGH severity. Confirmed from test data in `reports/queue.md` — both reports had identical timestamps.
- The 50-char truncation at word boundary makes slug collisions more likely for similar queries.
- Claude cannot generate unique microsecond values because it doesn't have a real clock.

## Proposed Solutions

### Option A: Add batch index suffix (Recommended)
Append `-1`, `-2`, `-3` based on launch order within the batch.
```
reports/{sanitized_query}_{YYYY-MM-DD}_{HHMMSS}_{index}.md
```
- **Pros:** Trivial to specify, deterministic, eliminates collision
- **Cons:** Slightly different format from CLI's auto-save paths
- **Effort:** Small
- **Risk:** Low

### Option B: Use random suffix
Append 4-6 random hex characters instead of microseconds.
- **Pros:** Unique without needing a counter
- **Cons:** Non-deterministic, harder to correlate with launch order
- **Effort:** Small
- **Risk:** Low

## Recommended Action

Option A — add batch index suffix.

## Technical Details

- **Affected files:** `.claude/skills/research-queue.md`
- **Components:** Step 5 (output path generation)

## Acceptance Criteria

- [ ] Parallel queries with similar names get unique output paths
- [ ] Batch index (1, 2, 3) appended to each filename in launch order

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-26 | Created from code review | architecture-strategist finding confirmed by test data |

## Resources

- PR: feat/background-research-agents
- Test data: reports/queue.md shows identical timestamps for parallel queries
