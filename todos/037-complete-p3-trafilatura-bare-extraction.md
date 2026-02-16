---
status: complete
priority: p3
issue_id: "037"
tags: [code-review, performance]
dependencies: []
---

# Use trafilatura bare_extraction for Single Parse

## Problem Statement

`extract.py` calls `trafilatura.extract()` and `trafilatura.extract_metadata()` separately, parsing HTML twice. Using `bare_extraction()` returns both content and metadata in a single parse.

## Findings

- **Source:** Performance Oracle agent
- **Location:** `research_agent/extract.py`

## Proposed Solutions

### Option A: Switch to bare_extraction() (Recommended)
Single call returns dict with `text`, `title`, `author`, `date`, etc.
- **Effort:** Small (30 min)

## Acceptance Criteria

- [ ] Single `bare_extraction()` call replaces separate extract + metadata
- [ ] Same content and metadata produced
- [ ] All tests pass
