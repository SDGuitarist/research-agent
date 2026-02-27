---
status: done
priority: p2
issue_id: "060"
tags: [code-review, architecture, agent-native]
dependencies: []
---

# P2: High-level API (run_research/run_research_async) has no context parameter

## Problem Statement

The public API functions `run_research()` and `run_research_async()` in `__init__.py` create a `ResearchAgent` without passing `context_path` or `no_context`. A programmatic caller using the documented public API cannot select a context, skip context, or prevent auto-detection.

## Findings

- Flagged by: agent-native-reviewer (WARNING)
- The low-level `ResearchAgent.__init__` accepts both params — full parity there
- But the high-level API (the one in `__all__`) has zero context control
- Also: `list_available_contexts` and `resolve_context_path` not exported in `__all__`

## Proposed Solutions

### Option A: Add context parameter to high-level API (Recommended)
```python
async def run_research_async(
    query: str, mode: str = "standard", context: str | None = None
) -> ResearchResult:
    context_path = None
    no_context = False
    if context is not None:
        context_path = resolve_context_path(context)
        if context_path is None:
            no_context = True
    agent = ResearchAgent(mode=research_mode, context_path=context_path, no_context=no_context)
```
- Pros: Full agent-native parity at the public API level
- Cons: Slightly enlarges public API surface
- Effort: Small (~10 lines)
- Risk: Low

## Recommended Action

Option A, plus export `list_available_contexts` and `resolve_context_path` in `__all__`.

## Technical Details

- **Affected files:** `research_agent/__init__.py`

## Acceptance Criteria

- [ ] `run_research("query", context="pfe")` uses the named context
- [ ] `run_research("query", context="none")` skips context
- [ ] `run_research("query")` auto-detects (existing behavior)
- [ ] `list_available_contexts` and `resolve_context_path` importable from package

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-26 | Created from code review | Agent-native parity gap |
