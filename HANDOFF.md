# Handoff: Cycle 19 MCP Server — Review Complete

## Current State

**Project:** Research Agent
**Phase:** Review complete — Cycle 19
**Branch:** `main`
**Date:** February 28, 2026
**Commit:** `c7d9ce1` (no new commits — review only)

---

## What Was Done This Session

Ran `/workflows:review` on the full Cycle 19 diff (`c7bbd85..HEAD`, 10 commits, 20 files). Launched 7 review agents in parallel:

1. **kieran-python-reviewer** — 0 P1, 3 P2, 1 P3
2. **security-sentinel** — 1 P1, 3 P2, 2 P3, 1 P4
3. **performance-oracle** — No issues (DNS cache change confirmed non-regression)
4. **architecture-strategist** — No blocking issues (clean layering, additive pattern upheld)
5. **agent-native-reviewer** — 3 critical parity gaps, 4 warnings
6. **code-simplicity-reviewer** — 1 redundant test class (43 lines)
7. **learnings-researcher** — 10 relevant patterns from past cycles, all correctly applied

### Files Created

- `docs/reviews/cycle-19-mcp-server/REVIEW-SUMMARY.md` — Full synthesis with recommended fix order
- `todos/089-pending-p1-unauthenticated-http-transport.md`
- `todos/090-pending-p2-path-stripping-regex-gaps.md`
- `todos/091-pending-p2-fstring-logger-calls-agent.md`
- `todos/092-pending-p2-auto-save-test-assert-gap.md`
- `todos/093-pending-p2-mode-validation-mcp-boundary.md`
- `todos/094-pending-p2-missing-critique-report-tool.md`
- `todos/095-pending-p2-missing-skip-critique-max-sources.md`
- `todos/096-pending-p3-remove-redundant-validate-tests.md`
- `todos/097-pending-p3-context-param-normalization.md`
- `todos/098-pending-p3-enrich-mcp-instructions.md`
- `todos/099-pending-p3-tighten-fastmcp-version.md`

### Feed-Forward Risk Resolution

- **Plan risk** ("HTTP transport reconfiguration"): Confirmed working. Security reviewer flagged the deeper issue — no authentication on HTTP transport (089).
- **Work risk** ("auto-save test coverage"): Confirmed gap. Test patches `atomic_write` but never asserts it was called (092).

---

## Three Questions

1. **Hardest judgment call in this review?** Whether the agent-native parity gaps (missing critique_report, skip_critique, max_sources) should be P1 or P2. The agent-native reviewer scored these as "critical", but the Cycle 19 plan explicitly scoped 5 tools. These are real parity gaps but not regressions — they're missing features. P2 is correct: should fix, but doesn't block merging the current scope.

2. **What did you consider flagging but chose not to, and why?** The `except Exception` catch-all in `mcp_server.py:65`. Every reviewer noted it, and the learnings researcher confirmed the project convention against bare catch-alls. But the code explicitly documents why this is the one justified exception (MCP server boundary), and the comment references the CLAUDE.md rule.

3. **What might this review have missed?** The downstream prompt injection surface. The MCP server introduces a new entry point where queries originate from potentially untrusted MCP clients. The existing three-layer defense was designed for CLI input. Whether the threat model shift requires strengthening those defenses was not deeply audited.

---

## Next Phase

**Fix phase** — address review findings, starting with P1 (089) then P2s in order.

### Prompt for Next Session

```
Read docs/reviews/cycle-19-mcp-server/REVIEW-SUMMARY.md. Fix todos 089-099 using /fix-batched. Start with P1 (089 - unauthenticated HTTP transport), then P2s in recommended order: 090, 091, 092, 093, 094, 095. Relevant files: research_agent/mcp_server.py, research_agent/agent.py, tests/test_mcp_server.py, pyproject.toml.
```
