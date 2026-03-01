# Review Summary: Cycle 19 MCP Server

**Review target:** Diff range `c7bbd85..HEAD` (10 commits, 20 files, +2026/-2638 lines)
**Date:** 2026-02-28
**Branch:** main

## Prior Phase Risk

> **From plan:** "Whether mcp.settings.host/mcp.settings.port reconfiguration works reliably before run() for HTTP transport."

Addressed: The HTTP transport uses `mcp.run(transport="http", host=host, port=port)` which passes host/port directly to FastMCP's run method. This works correctly. However, the security reviewer flagged that HTTP transport has no authentication (Finding 089).

> **From work Session 3:** "Whether test coverage is sufficient for the auto-save path."

Confirmed gap: The auto-save test patches `atomic_write` but never asserts it was called with correct arguments (Finding 092).

## Findings Summary

- **Total Findings:** 11
- **P1 (Critical):** 1 — BLOCKS MERGE
- **P2 (Important):** 6 — Should Fix
- **P3 (Nice-to-Have):** 4 — Enhancements

## Review Agents Used

| Agent | Key Finding |
|-------|------------|
| kieran-python-reviewer | f-string logger calls, auto-save test gap, clean extraction |
| security-sentinel | Unauthenticated HTTP (P1), path-stripping regex gaps, CWD risk |
| performance-oracle | No issues — DNS cache change confirmed as non-regression |
| architecture-strategist | No blocking issues — clean layering, additive pattern upheld |
| agent-native-reviewer | 3 missing MCP tools/params for CLI parity, context ambiguity |
| code-simplicity-reviewer | Redundant test class (43 lines removable) |
| learnings-researcher | 10 relevant patterns from past cycles, all correctly applied |

## Known Patterns (from learnings-researcher)

The following past solutions are relevant and were correctly applied:
- `docs/solutions/security/context-path-traversal-defense-and-sanitization.md` — Two-layer path defense used in `_validate_report_filename`
- `docs/solutions/logic-errors/dead-catch-and-narrow-httpx-exceptions.md` — Exception ordering at server boundary
- `docs/lessons/security.md` — Bare `except Exception` only at process boundaries (correctly applied)

## Recommended Fix Order

| # | Issue | Priority | Why this order | Unblocks |
|---|-------|----------|---------------|----------|
| 1 | 089 - Unauthenticated HTTP transport | P1 | Highest risk — enables unauthenticated access to all tools and API keys | — |
| 2 | 090 - Path-stripping regex misses OS paths | P2 | Info leakage aids exploitation of 089; quick regex fix | — |
| 3 | 091 - f-string logger calls in agent.py | P2 | 5-line consistency fix, closes logging migration | — |
| 4 | 092 - Auto-save test assert gap | P2 | Closes feed-forward risk from Session 3; 1 line | — |
| 5 | 093 - No mode validation at MCP boundary | P2 | Defense-in-depth; 4-line early validation | — |
| 6 | 094 - Missing critique_report MCP tool | P2 | Largest agent-parity gap; critique loop unusable via MCP | 095 |
| 7 | 095 - Missing skip_critique + max_sources params | P2 | Completes agent parity for run_research tool | — |
| 8 | 096 - Remove redundant TestValidateReportFilename | P3 | 43 lines removable; integration tests already cover it | — |
| 9 | 097 - Context parameter defensive normalization | P3 | Prevents "None"/"null" string confusion | — |
| 10 | 098 - Enrich MCP instructions field | P3 | Copy-only change; improves agent discoverability | — |
| 11 | 099 - Tighten fastmcp version constraint | P3 | Prevent silent breakage on major version bump | — |

## What Went Well

1. **`report_store.py` extraction** — Clean separation, correct dependency direction, no circular imports
2. **print-to-logging migration** — Thorough (42 test patches removed), correct `%s` lazy formatting
3. **`synthesize.py` stderr choice** — Pragmatic decision to use `sys.stderr.write()` for streaming UX
4. **DNS cache refactoring** — Eliminates shared mutable state; per-call scope is correct
5. **`_validate_report_filename`** — 7-check defense-in-depth, all justified
6. **Test coverage** — 31 tests covering all 5 tools, error paths, path traversal, transport validation, stdio integration
7. **Deferred imports** — Correct pattern for MCP server startup performance
8. **Architecture** — Additive pattern maintained; MCP layers on without changing pipeline

## Three Questions

1. **Hardest judgment call in this review?** Whether the agent-native parity gaps (missing critique_report, skip_critique, max_sources) should be P1 or P2. The agent-native reviewer scored these as "critical", but the Cycle 19 plan explicitly scoped 5 tools. These are real parity gaps but not regressions — they're missing features. P2 is correct: should fix, but doesn't block merging the current scope.

2. **What did you consider flagging but chose not to, and why?** The `except Exception` catch-all in `mcp_server.py:65`. Every reviewer noted it, and the learnings researcher confirmed the project convention against bare catch-alls. But the code explicitly documents why this is the one justified exception (MCP server boundary), and the comment references the CLAUDE.md rule. This is the right call.

3. **What might this review have missed?** The downstream prompt injection surface. The MCP server introduces a new entry point where queries originate from potentially untrusted MCP clients rather than local CLI users. The existing three-layer defense (sanitize + XML boundaries + system prompt) was designed for CLI input. Whether the threat model shift from "local user" to "network MCP client" requires strengthening those defenses was not deeply audited because the pipeline modules were out of diff scope.
