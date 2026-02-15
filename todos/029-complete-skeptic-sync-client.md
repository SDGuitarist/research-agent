---
status: ready
priority: p2
issue_id: "029"
tags: [code-review, performance, async]
dependencies: []
---

# Skeptic Agents Use Sync Anthropic Client

## Problem Statement

`skeptic.py` uses synchronous `Anthropic()` client wrapped in `asyncio.to_thread()`, creating a thread-within-thread pattern. Converting to `AsyncAnthropic` with `asyncio.gather()` could save 5-10s in deep mode by running all three skeptic agents truly concurrently.

## Findings

- **Source:** Performance Oracle agent
- **Location:** `research_agent/skeptic.py`

## Proposed Solutions

### Option A: Convert to AsyncAnthropic + asyncio.gather (Recommended)
Replace sync client with async client. Run evidence, timing, and framing agents concurrently.
- **Effort:** Medium (1-2 hours)

## Acceptance Criteria

- [ ] Skeptic agents use `AsyncAnthropic` client
- [ ] All three agents run concurrently via `asyncio.gather`
- [ ] All tests pass
