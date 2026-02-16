---
title: "Validation Questions Between Work Sessions Surface Forward-Feeding Risks"
date: 2026-02-15
category: workflow
tags:
  - process
  - validation
  - session-management
  - review
  - compound-engineering
module: n/a (process pattern)
symptoms: |
  Bugs or design issues discovered late in a cycle, after multiple sessions
  have already built on shaky foundations. Post-implementation review finds
  issues that could have been caught between sessions.
severity: medium
summary: |
  Asking 3 targeted validation questions after each work session catches design
  risks early. Q3 ("least confident area + what test catches it") is the highest
  value question. Findings feed forward into the next session's prompt.
---

# Validation Questions Between Work Sessions Surface Forward-Feeding Risks

## Problem

In multi-session implementation cycles, bugs and design issues compound. A questionable decision in Session 1 gets built upon in Session 2, making it expensive to fix by Session 4. Post-cycle review catches these issues, but by then the code is committed and the fix is a separate commit.

## Solution

Ask 3 validation questions after each work session, before starting the next:

1. **Q1: "What changed from the plan?"** — Catches plan staleness. If the implementation diverged, the next session's plan section may also need adjustment.

2. **Q2: "What deviations or alternatives were rejected?"** — Surfaces implicit design decisions. Variant: "What deviations from the plan did you make?" catches plan staleness better than asking about alternatives.

3. **Q3: "What are you least confident about, and what test would catch it?"** — The highest-value question. Forces the implementer to identify the weakest point. In Cycle 18, this question after Session 1 directly identified the `_last_source_count` private attr access pattern as the riskiest area, which shaped the Session 2 prompt to include explicit testing for it.

## Observations from Cycle 18

### Feed-forward effect

Session 1's Q3 answer ("least confident about private attr access across modules") directly shaped the Session 2 prompt. Session 2 then included specific tests for the private attr contract, catching a potential regression point before it became a problem.

### Diminishing returns on mechanical sessions

The questions are most valuable on **design sessions** (Session 1: dataclasses, Session 2: public API) where decisions have downstream consequences. On **mechanical sessions** (Session 3: CLI extraction — mostly moving code) the questions yield less because there are fewer design decisions to validate.

### Q2 variant comparison

- "What alternatives did you reject?" — yields general design rationale
- "What deviations from the plan did you make?" — yields specific plan-vs-implementation gaps

The deviation variant is better for catching plan staleness. Use it.

## Pattern

```
After each work session, ask:
1. What changed from the plan?
2. What deviations from the plan did you make?
3. What are you least confident about? What test would catch it?

Then: incorporate answers into the next session's prompt.
```

## Related

- `docs/solutions/workflow/auto-compact-mid-cycle-risks.md` — related session management pattern
- Cycle 18 plan: `docs/plans/2026-02-15-feat-pip-installable-package-plan.md`
