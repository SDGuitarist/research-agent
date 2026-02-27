---
status: done
priority: p2
issue_id: "058"
tags: [code-review, quality]
dependencies: []
---

# P2: XML tag <business_context> in prompts mismatches generic context= parameter names

## Problem Statement

Session 3 renamed Python parameters from `business_context` to `context`, but the XML tags in LLM prompts still say `<business_context>`. This creates a maintenance trap: code-level naming is generic (`context`) but prompt-level naming is business-specific (`<business_context>`). If a non-business context is ever used, the tag will be actively misleading to the LLM.

## Findings

- Flagged by: kieran-python-reviewer (HIGH), architecture-strategist (LOW)
- Acknowledged in HANDOFF.md as a known risk
- Locations:
  - `synthesize.py` lines 170, 172, 459, 461, 588 — `<business_context>` tag
  - `skeptic.py` line 47 — `<business_context>` tag
  - `modes.py` lines 154, 157 — `Reference <business_context> if provided`
  - `decompose.py` line 98 — uses `<research_context>` (yet another name)

## Proposed Solutions

### Option A: Rename all to <research_context> (Recommended)
Unify the XML tag name across all prompt templates. Use `<research_context>` since it's generic and descriptive.
- Pros: Consistent, generic, matches code-level naming intent
- Cons: Changes what the LLM sees (but LLMs are not sensitive to specific tag names)
- Effort: Small (~10 lines across 3 files)
- Risk: Low

### Option B: Leave as-is (acknowledged tech debt)
- Pros: Zero risk of regression
- Cons: Growing inconsistency as more contexts are added
- Effort: None
- Risk: Low for now, grows over time

## Recommended Action

Option A — bounded scope, pure rename, no behavioral change.

## Technical Details

- **Affected files:** `research_agent/synthesize.py`, `research_agent/skeptic.py`, `research_agent/modes.py`, `research_agent/decompose.py`

## Acceptance Criteria

- [ ] All LLM prompts use `<research_context>` consistently
- [ ] System prompts reference `<research_context>` not `<business_context>`
- [ ] All existing tests pass (prompt content tests may need updating)

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-26 | Created from code review | Flagged risk from work phase, confirmed by two agents |
