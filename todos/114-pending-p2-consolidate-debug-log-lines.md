---
status: done
priority: p2
issue_id: "114"
tags: [code-review, quality, simplicity]
dependencies: []
unblocks: []
sub_priority: 2
---

# 114: Replace 7 per-call-site debug log lines with 1 summary log

## Problem Statement

Seven `logger.debug("Planning: <function> -> %s", self.mode.planning_model)` lines were added to `agent.py`, each logging the same frozen value at different call sites. Since `planning_model` is a field on a frozen dataclass, it cannot change between call sites within a single run. Logging the same constant 7 times is noise, not signal. The two back-to-back logs at lines 253-254 (before `asyncio.gather`) are especially redundant — both log the same value at the same timestamp.

**Why it matters:** Debug output becomes harder to scan. The 7 lines add ~6 net LOC with zero diagnostic value beyond what a single log at run start would provide.

## Findings

- **Source:** Code simplicity reviewer + Python reviewer (O2)
- **Evidence:** `research_agent/agent.py` lines 195, 253, 254, 438, 661, 937, 1008 — all log `self.mode.planning_model` which is immutable
- **Pattern:** Existing codebase does not log frozen config values at every call site — this is an anomaly

## Proposed Solutions

### Option A: Single summary log at research() entry (Recommended)
Add one `logger.debug("Model routing: synthesis=%s, planning=%s", self.mode.model, self.mode.planning_model)` at the top of `research()`. Remove all 7 per-call-site lines.

- **Pros:** -6 net LOC, same diagnostic value, cleaner debug output
- **Cons:** Lose per-call-site confirmation (but this is redundant with reading the code)
- **Effort:** Small (15 min)
- **Risk:** Very low

### Option B: Keep as-is for now, remove after verification phase
Leave the 7 lines until 10-20 real runs confirm routing, then remove in a follow-up commit.

- **Pros:** Extra safety during initial rollout
- **Cons:** Defers cleanup, adds tech debt
- **Effort:** None now, small later
- **Risk:** None

## Recommended Action

_To be filled during triage_

## Technical Details

**Affected files:**
- `research_agent/agent.py` — lines 195, 253, 254, 438, 661, 937, 1008

**Change scope:** Remove 7 lines, add 1 line at top of `research()` method

## Acceptance Criteria

- [ ] Only 1 debug log line for model routing exists in agent.py
- [ ] Debug log shows both `model` and `planning_model` values
- [ ] All 871 tests pass
- [ ] `-v` flag still shows routing info in output

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-03-03 | Created from Cycle 21 review | 7 identical frozen-value logs are YAGNI |

## Resources

- Commit: 435dd2e
- Simplicity reviewer finding
- Python reviewer observation O2
