---
status: done
priority: p2
issue_id: "078"
tags: [code-review, simplification, architecture]
dependencies: []
unblocks: []
sub_priority: 2
---

# P2: Remove legacy PFE-specific fallback branches from synthesize.py

## Problem Statement

Three locations in `synthesize.py` still contain PFE-specific hardcoded text that should have been removed as part of the template decoupling:

1. **`synthesize_final()` lines 554-572**: The `elif context` branch hardcodes "Competitive Implications" and "Positioning Advice" section names for context-without-template cases. This is dead code with PFE assumptions — the `else` (generic) branch handles no-template correctly.

2. **`synthesize_report()` lines 226-230**: Fallback `context_instruction` mentions "Competitive Implications and Positioning Advice sections."

3. **`synthesize_final()` lines 500-504**: Same PFE-specific section names in fallback `context_instruction`.

## Findings

- Flagged by: code-simplicity-reviewer (Finding 1 + Finding 2), architecture-strategist (Finding 2)
- The `elif context` branch is 18 lines that can be removed entirely
- The fallback `context_instruction` strings are 2 string changes to make generic
- These are the last PFE-specific strings in `synthesize.py`

## Proposed Solutions

### Option A: Remove legacy branch + genericize fallback strings (Recommended)

1. Delete the `elif context` branch (lines 554-572) — context without template falls through to the `else` generic branch
2. Change fallback `context_instruction` in `synthesize_report()` to: "Use business context for analytical and recommendation sections. Keep factual analysis objective and context-free."
3. Change fallback `context_instruction` in `synthesize_final()` to: "Use the business context for analytical and recommendation sections. Reference specific positioning, threats, opportunities, and actionable recommendations."

- **Pros:** Completes the decoupling goal, removes 18 lines, no PFE-specific strings remain
- **Cons:** Context-without-template now gets generic sections instead of business-intelligence sections. This is actually more correct behavior.
- **Effort:** Small (~20 lines changed/removed)
- **Risk:** Low — verify test coverage for the context-without-template path

## Technical Details

**Affected files:**
- `research_agent/synthesize.py` lines 226-230, 500-504, 554-572

## Acceptance Criteria

- [ ] No PFE-specific section names remain in `synthesize.py`
- [ ] `synthesize_final()` has 2-way branch (template / no-template) instead of 4-way
- [ ] Fallback context instructions are generic
- [ ] All existing tests still pass (update any that assert PFE section names)

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-27 | Created from code review | Flagged by Code Simplicity + Architecture Strategist |
