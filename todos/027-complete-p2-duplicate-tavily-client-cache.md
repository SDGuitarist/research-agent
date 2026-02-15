---
status: complete
priority: p2
issue_id: "027"
tags: [code-review, quality, duplication]
dependencies: []
---

# Duplicate Tavily Client Cache

## Problem Statement

`search.py` (lines 27-29, 81-89) and `cascade.py` (lines 29-31, 46-54) contain identical `_get_tavily_client()` functions with identical globals. Two separate TavilyClient instances exist. Flagged by 4/6 review agents.

## Findings

- **Source:** Kieran Python, Pattern Recognition, Architecture Strategist, Simplicity Reviewer
- **Location:** `research_agent/search.py:27-29,81-89`, `research_agent/cascade.py:29-31,46-54`

## Proposed Solutions

### Option A: Keep in search.py, import in cascade.py (Recommended)
- **Effort:** Small (30 min)

## Acceptance Criteria

- [ ] Single `_get_tavily_client` function exists
- [ ] Both search and cascade use the shared client
- [ ] All tests pass
