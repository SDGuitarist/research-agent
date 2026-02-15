---
status: pending
priority: p2
issue_id: "032"
tags: [code-review, quality, consistency]
dependencies: []
---

# Inconsistent Frozen Dataclasses

## Problem Statement

5 dataclasses are not frozen despite never being mutated after construction: `SearchResult`, `FetchedPage`, `Summary`, `ExtractedContent`, `SkepticFinding`. Other dataclasses in the project (e.g., `ModeConfig`, `CycleConfig`) are correctly frozen.

## Findings

- **Source:** Pattern Recognition Specialist agent
- **Location:** `research_agent/search.py`, `research_agent/fetch.py`, `research_agent/summarize.py`, `research_agent/extract.py`, `research_agent/skeptic.py`

## Proposed Solutions

### Option A: Add frozen=True to all 5 (Recommended)
```python
@dataclass(frozen=True)
```
- **Effort:** Small (15 min)

## Acceptance Criteria

- [ ] All 5 dataclasses are frozen
- [ ] No code mutates them after construction (verify)
- [ ] All tests pass
