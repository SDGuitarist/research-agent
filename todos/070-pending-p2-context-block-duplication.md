---
status: done
priority: p2
issue_id: "070"
tags: [code-review, duplication]
dependencies: ["065"]
---

# P2: Context block building duplicated across 3 files

## Problem Statement

The `<research_context>` XML block building pattern is copy-pasted in 4 places across 3 files. `skeptic.py` has a clean `_build_context_block()` helper, but other modules don't use it.

## Findings

- Flagged by: pattern-recognition-specialist (P2)
- Locations: `synthesize.py:167-175,456-464`, `decompose.py:90-97`, `skeptic.py:42-47`
- Related to todo 065 (sanitize at load boundary) — fixing 065 first simplifies this

## Fix

Extract `_build_context_block()` from `skeptic.py` into shared `sanitize.py` or new `prompt_helpers.py`. Import in all 3 files.

## Acceptance Criteria

- [ ] Single `build_context_block(content: str) -> str` function
- [ ] All 3 files import and use it
- [ ] XML tag name is defined once (not repeated as string literal)

## Technical Details

- **Affected files:** `research_agent/synthesize.py`, `decompose.py`, `skeptic.py`, new shared module
- **Effort:** Small (~15 lines)
