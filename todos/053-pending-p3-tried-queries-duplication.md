---
status: done
priority: p3
issue_id: "053"
tags: [code-review, quality]
dependencies: []
---

# P3: `tried_queries` construction duplicated between deep and standard

## Problem Statement

`agent.py:692-697` and `agent.py:774-779` contain identical 5-line blocks building the `tried` list. Should be extracted to a helper like `_collect_tried_queries(query, refined_query, decomposition)`.

## Findings

- Flagged by: pattern-recognition-specialist

## Proposed Solutions

Extract a 5-line helper method.
- Effort: Trivial
- Risk: None

## Technical Details

- **File:** `research_agent/agent.py:692-697, 774-779`

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-25 | Created from review | — |
