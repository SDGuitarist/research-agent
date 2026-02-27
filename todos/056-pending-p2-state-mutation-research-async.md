---
status: done
priority: p2
issue_id: "056"
tags: [code-review, architecture, quality]
dependencies: []
---

# P2: _research_async mutates self.context_path and self.no_context — latent reuse bug

## Problem Statement

`_research_async()` in `agent.py:231-241` mutates `self.context_path` and `self.no_context` during auto-detection. Unlike other per-run state (which is reset at the top of the method), these are NOT reset between calls. Calling `research()` twice on the same `ResearchAgent` produces different behavior on the second call.

## Findings

- Flagged by: kieran-python-reviewer (CRITICAL), architecture-strategist (MEDIUM), code-simplicity-reviewer (MEDIUM), agent-native-reviewer (WARNING)
- The first call's auto-detection permanently changes the agent's configuration
- `_step_num`, `_current_schema_result`, etc. ARE reset at the top — but `context_path` and `no_context` are NOT
- The agent-native reviewer notes this breaks agent reuse for batch queries

## Proposed Solutions

### Option A: Use local variables (Recommended)
Use local variables in `_research_async()` for effective context state. Pass them where needed instead of reading from `self`.
```python
async def _research_async(self, query: str) -> str:
    # ... existing resets ...
    effective_context_path = self.context_path
    effective_no_context = self.no_context

    if effective_context_path is None and not effective_no_context and CONTEXTS_DIR.is_dir():
        detected = await asyncio.to_thread(...)
        if detected is not None:
            effective_context_path = detected
        else:
            effective_no_context = True
```
- Pros: Makes the agent reentrant, preserves user's original configuration
- Cons: Need to thread local variables through internal methods
- Effort: Medium (~15 lines)
- Risk: Low

### Option B: Reset at top of _research_async
Save original values in `__init__` and reset at the start of each run.
- Pros: Simpler, maintains current self-based access pattern
- Cons: Adds more instance attributes
- Effort: Small (~5 lines)
- Risk: Low

## Recommended Action

Option A — cleaner data flow, explicitly separates user config from runtime decisions.

## Technical Details

- **Affected files:** `research_agent/agent.py`

## Acceptance Criteria

- [ ] Calling `research()` twice on the same agent with different queries produces correct auto-detection for each
- [ ] Original `self.context_path` and `self.no_context` are unchanged after `research()` returns
- [ ] Test verifying agent reuse with auto-detection

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-26 | Created from code review | Four agents flagged this independently |
