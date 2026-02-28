---
status: pending
priority: p3
issue_id: "086"
tags: [code-review, quality, tests]
dependencies: ["085"]
unblocks: []
sub_priority: 1
---

# P3: Stale test name `test_skips_section_11_when_no_findings`

## Problem Statement

Test name references "section 11" but the refactoring moved generic section numbering to start at 5. The test body still passes (asserts `"11. **Adversarial Analysis**" not in prompt`, which is true because the number is now 5 when present and absent when `skeptic_findings=[]`), but the name is misleading.

## Findings

- Flagged by: kieran-python-reviewer (P3), also noted in HANDOFF Three Questions
- `tests/test_synthesize.py` line ~505: `test_skips_section_11_when_no_findings`
- The assertion `"11. **Adversarial Analysis**" not in prompt` passes vacuously — neither 11 nor 5 appears when skeptic is empty
- Dependent on #085: if prompt wording changes, this test name should change too

## Proposed Solutions

### Option A: Rename test (Recommended)
- Rename to `test_skips_adversarial_analysis_when_no_findings`
- Update assertion to check `"**Adversarial Analysis**" not in` the section list portion
- **Effort:** Small (rename + 1 assertion edit)

## Technical Details

**Affected files:**
- `tests/test_synthesize.py` — test name and assertion (~line 505)

## Acceptance Criteria

- [ ] Test name does not reference "Section 11"
- [ ] Assertion still correctly verifies skeptic section is absent
- [ ] All tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-28 | Created from P2 triage review | Linked to #085 |
