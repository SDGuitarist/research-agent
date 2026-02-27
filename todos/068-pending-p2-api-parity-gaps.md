---
status: done
priority: p2
issue_id: "068"
tags: [code-review, agent-native, api]
dependencies: []
---

# P2: API parity gaps — 6 CLI features not exposed programmatically

## Problem Statement

Agents using the Python API cannot: list reports, critique reports, view critique history, skip critique, override source count, or append to research log. Functions exist internally but are not exported in `__init__.py`.

## Findings

- Flagged by: agent-native-reviewer (P2)
- 4 of 6 gaps are pre-existing (not introduced by this PR)
- Agent-native score: 12/18 capabilities accessible

## Fix

1. Export in `__init__.py.__all__`:
   - `list_reports() -> list[ReportInfo]` (needs refactor from stdout printer to data returner)
   - `critique_report_file` and `CritiqueResult`
   - `load_critique_history`
2. Add params to `run_research()` and `run_research_async()`:
   - `skip_critique: bool = False`
   - `max_sources: int | None = None`

## Acceptance Criteria

- [ ] `list_reports()` returns structured data (not prints to stdout)
- [ ] `critique_report_file` importable from `research_agent`
- [ ] `run_research(query, skip_critique=True)` works
- [ ] `run_research(query, max_sources=5)` works

## Technical Details

- **Affected files:** `research_agent/__init__.py`, `research_agent/cli.py`
- **Effort:** Medium (~30 lines)
