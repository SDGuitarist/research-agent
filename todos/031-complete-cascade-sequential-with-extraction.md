---
status: ready
priority: p2
issue_id: "031"
tags: [code-review, performance, async]
dependencies: ["028"]
---

# Cascade Recovery Sequential with Extraction

## Problem Statement

Cascade recovery waits for `extract_all` to complete before starting. These could overlap using `asyncio.gather` for 2-10s savings on fetches with many failed URLs.

## Findings

- **Source:** Performance Oracle agent
- **Location:** `research_agent/agent.py` (orchestration of cascade + extraction)

## Proposed Solutions

### Option A: Overlap cascade and extraction with asyncio.gather (Recommended)
Run cascade recovery concurrently with extraction of already-fetched pages.
- **Effort:** Medium (1 hour)
- **Depends on:** 028 (extract_all must be thread-safe first)

## Acceptance Criteria

- [ ] Cascade recovery and extraction overlap where possible
- [ ] Results are correctly merged
- [ ] All tests pass
