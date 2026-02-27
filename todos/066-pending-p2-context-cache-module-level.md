---
status: done
priority: p2
issue_id: "066"
tags: [code-review, architecture, thread-safety]
dependencies: []
---

# P2: Module-level context cache — thread safety, size, test pollution

## Problem Statement

`_context_cache` in `context.py:23` is a module-level dict shared across all `ResearchAgent` instances. No thread safety, no size bound, no eviction policy.

## Findings

- Flagged by 6 agents independently (highest cross-agent agreement in this review)
- `clear_context_cache()` creates cross-instance side effects in concurrent use
- No max size — grows unbounded in long-running processes
- Tests rely on `tmp_path` uniqueness to avoid cache pollution

## Fix Options

**Option A (Recommended):** Move cache to `ResearchAgent` instance attribute.
**Option B:** Use `functools.lru_cache(maxsize=32)` with a wrapper.
**Option C:** Document as not thread-safe (acceptable for v1).

## Acceptance Criteria

- [ ] Two concurrent `ResearchAgent` instances don't interfere via cache
- [ ] Cache has a maximum size (32 or similar)
- [ ] Tests don't depend on cache isolation via path uniqueness

## Technical Details

- **Affected files:** `research_agent/context.py`, `research_agent/agent.py`, tests
- **Effort:** Medium (~15 lines)
