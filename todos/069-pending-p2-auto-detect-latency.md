---
status: done
priority: p2
issue_id: "069"
tags: [code-review, performance]
dependencies: []
---

# P2: Auto-detect LLM call adds 1-3s latency to every run

## Problem Statement

When no `--context` flag is given and `contexts/` exists, `auto_detect_context()` makes a Sonnet API call. Adds 1-3 seconds before any research begins. Uses full Sonnet for a trivial classification task.

## Findings

- Flagged by: performance-oracle (P1 performance)
- Classification task doesn't need Sonnet — Haiku is sufficient
- Single-file directory needs no LLM call at all

## Fix Options

1. Use Haiku for auto-detection (~0.3s vs ~2s)
2. Short-circuit when `contexts/` has exactly one `.md` file — no LLM call needed
3. Cache auto-detect result per query hash to disk

## Acceptance Criteria

- [ ] Auto-detect uses Haiku (or faster model)
- [ ] Single-context directory skips LLM call entirely
- [ ] Latency under 0.5s for typical auto-detect

## Technical Details

- **Affected files:** `research_agent/context.py`, `research_agent/agent.py`
- **Effort:** Small-Medium (~15 lines)
