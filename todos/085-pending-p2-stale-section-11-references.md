---
status: pending
priority: p2
issue_id: "085"
tags: [code-review, quality, correctness]
dependencies: []
unblocks: ["086"]
sub_priority: 1
---

# P2: Stale "Section 11" references in synthesize.py

## Problem Statement

The `synthesize_final` docstring and prompt strings reference sections 9-12/13 and "Section 11 (Adversarial Analysis)", but the generic (non-template) path now starts final sections at 5 via `_DEFAULT_FINAL_START`. The docstring claims "sections 1-8" draft and "sections 9+" final, which no longer matches any code path. The hardcoded "Section 11" in prompt text sent to the LLM creates ambiguity between the numbered section list and the prose instruction.

## Findings

- Flagged by: kieran-python-reviewer (P2), 3 agents confirmed
- `synthesize.py` docstring at line ~459: "Produce sections 9-12/13"
- `synthesize.py` prompt strings: "For Section 11 (Adversarial Analysis)"
- `synthesize.py` inline comment: "skip Section 11"
- After refactoring, generic path uses `_DEFAULT_FINAL_START = 5`, so Adversarial Analysis is section 5
- Template path numbering depends on `draft_count` parameter (variable)
- Known Pattern: learnings-researcher found no past solutions about this specific issue

## Proposed Solutions

### Option A: Replace section numbers with section names in prompts (Recommended)
- Change `"For Section 11 (Adversarial Analysis)"` → `"For the **Adversarial Analysis** section"`
- Change `"skip Section 11"` → `"skip the Adversarial Analysis section"`
- Update docstring to describe intent without hardcoded numbers
- **Pros:** Works for both template and generic paths regardless of numbering
- **Cons:** Minor wording change in LLM prompt
- **Effort:** Small (5-6 line edits in synthesize.py)
- **Risk:** Low — LLM can see the actual numbered list in the prompt

### Option B: Keep numbers but make them dynamic
- Pass section numbers as variables into the prompt strings
- **Pros:** Precise numbering
- **Cons:** Adds complexity; prompt text becomes harder to read
- **Effort:** Medium
- **Risk:** Low

## Technical Details

**Affected files:**
- `research_agent/synthesize.py` — docstring (~line 459), prompt strings (~lines 477, 530, 542, 548)

## Acceptance Criteria

- [ ] No hardcoded "Section 11" in synthesize.py prompt strings
- [ ] Docstring accurately describes the function's behavior
- [ ] All tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-28 | Created from P2 triage review | Flagged by 3/6 review agents |
