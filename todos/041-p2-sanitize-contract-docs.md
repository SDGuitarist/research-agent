---
id: "041"
status: done
severity: P2
title: Fix sanitization contract documentation and consistency
source: docs/reviews/p3-do-now-fixes/REVIEW-SUMMARY.md
---

# P2: Fix sanitization contract documentation and consistency

## Problem

After removing redundant `sanitize_content()` calls in decompose.py and relevance.py, the convention is inconsistent and underdocumented:

1. `relevance.py:122` comment references nonexistent `score_and_filter_sources` (should be `evaluate_sources`)
2. `decompose.py:141` has no comment documenting the pre-sanitized contract
3. `score_source` docstring says "original research query" but now expects pre-sanitized input
4. `synthesize.py:413,497` still double-sanitizes (and `sanitize_content` is NOT idempotent — creates `&amp;amp;`)

## Fix

1. Fix comment at `relevance.py:122` → `# query is pre-sanitized by caller (evaluate_sources)`
2. Add comment in `decompose.py:141` → `# critique_guidance is pre-sanitized by load_critique_history`
3. Update `score_source` docstring to note pre-sanitization precondition
4. Remove double-sanitization in `synthesize.py` (same pattern as decompose/relevance fix)

## Files
- research_agent/relevance.py
- research_agent/decompose.py
- research_agent/synthesize.py
