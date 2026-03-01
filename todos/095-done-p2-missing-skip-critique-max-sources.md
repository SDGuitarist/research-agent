---
status: done
priority: p2
issue_id: "095"
tags: [code-review, agent-native]
dependencies: []
unblocks: []
sub_priority: 6
---

# Missing skip_critique and max_sources Parameters on run_research

## Problem Statement

The `run_research_async` public API accepts `skip_critique: bool` and `max_sources: int | None`, but the MCP `run_research` tool does not expose these parameters. Agents cannot:
- Opt out of the critique API call to save latency and ~$0.02 per query
- Fine-tune source count independently of mode selection

## Findings

- **Source:** agent-native-reviewer
- **Public API:** `research_agent/__init__.py:91-92` — `skip_critique` and `max_sources` params exist
- **CLI:** `--no-critique` and `--max-sources` flags available
- **MCP:** Neither parameter exposed

## Proposed Solutions

### Option A: Add both parameters to run_research (Recommended)
```python
async def run_research(
    query: str,
    mode: str = "standard",
    context: str | None = None,
    skip_critique: bool = False,
    max_sources: int | None = None,
) -> str:
```
- **Effort:** Small (2 lines in signature + pass-through to `run_research_async`)
- **Risk:** None — additive change

## Acceptance Criteria

- [ ] `skip_critique` parameter available on `run_research` tool
- [ ] `max_sources` parameter available on `run_research` tool
- [ ] Tests cover both new parameters

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-28 | Created from agent-native-reviewer | Quick win for agent parity |
