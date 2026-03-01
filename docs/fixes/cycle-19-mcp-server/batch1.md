# Batch 1: Security + Quality (089, 090, 091)

**Commit:** `6ca586c`
**Files changed:** `research_agent/mcp_server.py`, `research_agent/agent.py`, `tests/test_mcp_server.py`

### Prior Phase Risk

> "What might this review have missed? The downstream prompt injection surface. The MCP server introduces a new entry point where queries originate from potentially untrusted MCP clients rather than local CLI users."

Addressed by 089: hard error for non-loopback HTTP binding eliminates the network attack surface. The existing three-layer defense (sanitize + XML boundaries + system prompt) remains appropriate for the localhost-only threat model. Prompt injection via MCP clients is tracked as a future concern but not actionable in this fix cycle.

### Fixes Applied

**089 — Unauthenticated HTTP transport (P1)**
- Changed non-localhost HTTP binding from a warning to a hard `sys.exit()` with guidance
- Added `::1` (IPv6 loopback) to the allowed set
- Added `test_non_localhost_http_refused` test
- Chose Option C (localhost-only) over Option A (bearer token) — simpler, no middleware needed, eliminates the attack surface entirely for the common case

**090 — Path-stripping regex gaps (P2)**
- Broadened regex from `/Users/|/home/` to a multi-segment Unix path pattern
- Uses negative lookbehind `(?<!:/)(?<!/)` to avoid matching URLs
- Added `test_path_stripping_covers_common_unix_paths` test

**091 — f-string logger calls (P2)**
- Converted all 7 f-string logger calls in agent.py to `%s` lazy formatting
- Includes 5 `logger.warning()` calls (as specified) plus 2 `logger.info()` calls found during the fix
- Zero f-string logger calls remain in agent.py

## Three Questions

1. **Hardest fix in this batch?** The path-stripping regex (090). The broader pattern `(?<!:/)(?<!/)/(?:[\w.-]+/)+[\w.-]+` correctly catches multi-segment Unix paths while avoiding URLs, but the negative lookbehind logic required careful testing. A simpler `/\S+` approach would over-strip URLs in error messages.

2. **What did you consider fixing differently, and why didn't you?** For 089, considered requiring `MCP_AUTH_TOKEN` (Option A) for HTTP transport. Rejected because FastMCP's HTTP transport doesn't expose middleware hooks for auth validation, so we'd need to monkey-patch or fork — over-engineering for a local research tool. Localhost-only is sufficient.

3. **Least confident about going into the next batch or compound phase?** The path regex negative lookbehind — it handles `://` URLs correctly but edge cases like error messages containing both a URL and a filesystem path haven't been exhaustively tested. The test covers the common case.
