# Handoff: Cycle 19 MCP Server — Fix Phase Complete

## Current State

**Project:** Research Agent
**Phase:** Fix-batched complete — Cycle 19
**Branch:** `main`
**Date:** February 28, 2026
**Commits:** `6ca586c`, `d68c72c`, `96e3fe2` (3 batch commits)

---

## What Was Done This Session

Fixed all 11 review findings from `docs/reviews/cycle-19-mcp-server/REVIEW-SUMMARY.md` in 3 batches:

### Batch 1 — Security + Quality (089, 090, 091)
- **089 (P1):** Blocked non-localhost HTTP binding with hard `sys.exit()` — eliminates unauthenticated network access
- **090 (P2):** Broadened path-stripping regex to catch `/opt/`, `/var/`, `/tmp/`, `/app/` paths
- **091 (P2):** Converted all 7 f-string logger calls in agent.py to `%s` lazy formatting

### Batch 2 — Test + Validation + Agent Parity (092, 093, 094, 095)
- **092 (P2):** Added `assert_called_once_with` for atomic_write in auto-save test
- **093 (P2):** Added `VALID_MODES` early validation at MCP boundary
- **094 (P2):** Added `critique_report` MCP tool (6th tool, wraps public API)
- **095 (P2):** Added `skip_critique` and `max_sources` params to `run_research`

### Batch 3 — Cleanup + Polish (096, 097, 098, 099)
- **096 (P3):** Removed redundant `TestValidateReportFilename` class (-43 lines), migrated unique test
- **097 (P3):** Added context param normalization (`"null"`/`""` → `None`)
- **098 (P3):** Enriched MCP instructions to mention all 6 tools
- **099 (P3):** Tightened fastmcp version to `>=2.0,<3.0`

### Files Changed
- `research_agent/mcp_server.py` — All 3 batches
- `research_agent/agent.py` — Batch 1 (f-string loggers)
- `tests/test_mcp_server.py` — All 3 batches
- `pyproject.toml` — Batch 3 (version pin)
- 11 todo files renamed from `pending` to `done`

### Test Results
- Full suite: 802 tests passing (pre-commit hook runs all)
- MCP server tests: 33 tests (was 31, added 8 new, removed 7 redundant, +1 migrated)

---

## Three Questions

1. **Hardest fix in this batch?** The path-stripping regex (090). Balancing coverage (catching `/opt/`, `/var/`, `/tmp/`) against over-matching (not stripping URLs) required a regex with negative lookbehind `(?<!:/)(?<!/)` that's correct but not immediately obvious.

2. **What did you consider fixing differently, and why didn't you?** For 089, considered requiring `MCP_AUTH_TOKEN` bearer token for HTTP transport (Option A from the todo). Rejected because FastMCP doesn't expose middleware hooks for auth validation — implementing it would require monkey-patching or forking the library. Localhost-only restriction is simpler and sufficient for a local research tool.

3. **Least confident about going into the compound phase?** The critique_report tool's catch-all `except Exception`. It follows the justified server-boundary pattern, but it's now the second such catch-all in the file. If `critique_report_file` changes its exception types, errors would be silently caught. This is acceptable risk for a tool that's non-critical to the research pipeline.

---

## Next Phase

**Compound phase** — document solutions from this fix cycle in `docs/solutions/`.

### Prompt for Next Session

```
Read docs/fixes/cycle-19-mcp-server/batch1.md, batch2.md, batch3.md. Run /workflows:compound to document the key patterns from fixing 11 review findings. Focus on: (1) MCP server boundary security patterns, (2) agent-native parity checklist, (3) defensive input normalization for LLM callers. Relevant files: research_agent/mcp_server.py, docs/fixes/cycle-19-mcp-server/.
```
