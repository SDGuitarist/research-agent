---
status: done
priority: p1
issue_id: "089"
tags: [code-review, security]
dependencies: []
unblocks: []
sub_priority: 1
---

# Unauthenticated HTTP Transport

## Problem Statement

When `MCP_TRANSPORT=http`, the MCP server binds to a configurable host/port with zero authentication. Any process on the network (or localhost) can invoke all 5 tools — running expensive research queries (consuming API keys), reading saved reports, and causing denial of service. The code logs a warning for non-localhost binding, but a warning is not a security control.

**Why it matters:** This is an open proxy for web research with API key consumption. Even on localhost, other local processes (browser extensions, compromised apps) can reach it.

## Findings

- **Source:** security-sentinel review
- **File:** `research_agent/mcp_server.py`, lines 215-228
- **Evidence:** `mcp.run(transport="http", host=host, port=port)` with no auth middleware
- **Exploitability:** High — simple HTTP POST hits tools with no credentials required

## Proposed Solutions

### Option A: Bearer token from environment variable (Recommended)
- Read `MCP_AUTH_TOKEN` from env; refuse to start HTTP transport without it
- Add middleware or check in each tool that validates the token
- **Pros:** Simple, standard pattern, no new dependencies
- **Cons:** Token management is the user's responsibility
- **Effort:** Medium
- **Risk:** Low

### Option B: Refuse HTTP transport entirely for v1
- Remove the HTTP transport option; only allow stdio
- **Pros:** Eliminates the attack surface completely
- **Cons:** Blocks legitimate HTTP use cases (Claude Desktop, remote access)
- **Effort:** Small
- **Risk:** None

### Option C: Default-deny with localhost + rate limiting
- Keep HTTP but enforce `127.0.0.1` only (error, not warn, for other hosts)
- Add per-minute rate limiting to prevent API key abuse
- **Pros:** Balances security with usability
- **Cons:** Localhost-only limits deployment flexibility; rate limiting adds complexity
- **Effort:** Medium
- **Risk:** Low

## Recommended Action

_To be decided during triage._

## Technical Details

- **Affected files:** `research_agent/mcp_server.py`
- **Components:** HTTP transport configuration in `main()`

## Acceptance Criteria

- [ ] HTTP transport requires authentication or is restricted to localhost-only with hard error
- [ ] Unauthenticated requests receive 401/403 response
- [ ] Test verifies auth is enforced

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-28 | Created from security-sentinel review | First P1 in Cycle 19 review |

## Resources

- Review: `docs/reviews/cycle-19-mcp-server/REVIEW-SUMMARY.md`
- File: `research_agent/mcp_server.py:215-228`
