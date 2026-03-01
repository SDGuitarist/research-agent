# Cycle 19: MCP Server for Research Agent

**Date:** 2026-02-28
**Phase:** Brainstorm
**Source:** `docs/research/master-recommendations-future-cycles.md` (Cycle 19 section), `plans/Pacific Flow Intelligence Agent — System Specification.md`

---

## What We're Building

An MCP (Model Context Protocol) server that wraps the research agent's existing public API, letting any MCP-compatible client (Claude Code, Cursor, Claude Desktop) run research queries, browse saved reports, and check available modes — without touching the CLI.

The agent is already pip-installable (v0.18.0, Cycle 18 complete). The public async API (`run_research_async`) is MCP-ready. This cycle adds a thin MCP layer on top.

## Why This Approach

### Tool Design: Coarse Intent-Based (4 tools)

We're exposing **4 tools** that map to user intents, not pipeline stages:

| Tool | Wraps | Purpose |
|------|-------|---------|
| `run_research` | `run_research_async()` | Run a research query, get a markdown report back. Params: `query`, `mode`, `context` (optional). |
| `list_reports` | `get_reports()` | List saved reports with metadata |
| `get_report` | reads from `reports/` dir | Retrieve a specific saved report by filename |
| `list_modes` | `list_modes()` | Show available modes and their configs |

**Parameter decisions for `run_research`:**
- `context` — exposed as optional param. Critical for Pacific Flow context-aware research.
- `skip_critique`, `max_sources` — not exposed. Power-user knobs, can add later if needed.

**Why not expose `search`, `fetch`, `synthesize` separately?**
- The calling LLM shouldn't orchestrate the pipeline — that's the agent's job
- GPT-Researcher's gptr-mcp uses this same coarse pattern (5 tools over a complex pipeline)
- Fewer tools = better LLM tool selection accuracy (degrades past ~30 tools)
- Can always add standalone `search`/`fetch` escape hatches in a later cycle if needed

**Rejected alternative:** Hybrid (coarse + escape hatches). Adds complexity and testing surface for edge cases we don't have yet. YAGNI.

### Transport: Both (stdio + streamable HTTP)

- **stdio** — default, for Claude Code / Cursor / Claude Desktop
- **streamable HTTP** — for remote/multi-client deployment
- Selected via `MCP_TRANSPORT` environment variable, defaults to `stdio`
- SSE is deprecated (MCP spec 2025-03-26), not supported
- Both transports fully tested

### Execution: Blocking

- Tool calls block until research completes (10-90 seconds depending on mode)
- No async job pair (start/poll) — adds complexity for no current benefit
- 90 seconds is within MCP client timeout limits
- Can add `ctx.report_progress()` in a future cycle by wiring callbacks into the agent

### SDK: FastMCP (official Python SDK)

Using the `mcp` package (FastMCP merged into official SDK). Decorator-based tool registration with auto-generated schemas from type annotations.

## Blockers to Fix First

Two issues must be resolved before the MCP server can work:

### 1. stdout noise (CRITICAL for MCP)

`synthesize.py` uses `print()` to stream progress text to stdout. MCP's stdio transport uses stdout for protocol messages. Any rogue `print()` corrupts the protocol and crashes the server.

**Fix:** Convert all `print()` calls in `synthesize.py` to `logging.info()` or `logging.debug()`. The CLI can configure a console logging handler to preserve the current UX. The MCP server won't configure a console handler, so stdout stays clean.

### 2. Unbounded `_context_cache` (memory leak)

`_context_cache` in `context.py` grows without bound. In a short-lived CLI process, this doesn't matter. In a long-running MCP server, it's a memory leak.

**Fix:** Replace with `functools.lru_cache(maxsize=32)` or add a max-size check. Small change, ~10 lines.

## Key Decisions

1. **4 coarse tools** — one per user intent, not one per pipeline stage
2. **Both transports** — stdio (default) + streamable HTTP, env var switch, both tested
3. **Blocking execution** — no async job pair, no progress (for now)
4. **FastMCP decorator pattern** — type annotations + docstrings = tool schemas
5. **Thin wrapper** — MCP server file contains zero business logic, delegates to existing API
6. **Fix blockers in-cycle** — stdout noise and cache leak fixed as first sessions
7. **Error handling** — catch `ResearchError` and subclasses, return error strings (not raised exceptions)
8. **New dependency** — `mcp` package added to `pyproject.toml`. Verify no conflicts with existing deps during planning.

## Architecture

```
research_agent/
├── mcp_server.py    ← NEW: thin MCP wrapper (~80-100 lines)
├── __init__.py      ← existing public API (unchanged)
├── agent.py         ← unchanged
├── synthesize.py    ← FIX: print() → logging
├── context.py       ← FIX: bounded cache
└── ...              ← all other modules unchanged
```

The MCP server is a single new file plus two small fixes. No existing module interfaces change.

Entry point added to `pyproject.toml` as a console script (`research-agent-mcp`).

## Reference Implementations

| Project | Tools | Pattern | Takeaway |
|---------|-------|---------|----------|
| gptr-mcp | 5 tools + 1 resource | Coarse, full pipeline hidden | Our model — few tools, LLM doesn't orchestrate |
| Firecrawl MCP | 12 tools in 4 groups | Granular + async job pair | Async pattern useful for production, not needed yet |
| Anthropic Tool Search | `defer_loading: True` | Discovery for large catalogs | Not needed with 4 tools; useful if we grow past 10 |

## Testing Scope

- **stdio transport:** Unit tests with mocked tool calls + one integration test exercising the full stdio roundtrip
- **streamable HTTP transport:** Unit tests with mocked HTTP client + one integration test with a real HTTP server (start server in fixture, call tools, assert responses)
- **Both:** Error handling paths (invalid mode, empty query, missing API keys)

## Open Questions

None — all key decisions resolved during brainstorm dialogue.

## Feed-Forward

- **Hardest decision:** Tool granularity — coarse vs hybrid. The Cycle 19 doc recommended separate `search`/`fetch`/`synthesize` tools, but the research strongly favored coarse tools. We went coarse, accepting that we may need to revisit if downstream agents need standalone search.
- **Rejected alternatives:** (1) Hybrid tool design — adds complexity for unproven edge cases. (2) Async job pair — overengineering for Claude Code use. (3) SSE transport — deprecated. (4) Separate prep cycle for blockers — overhead of a separate plan/review not worth it for ~40 lines of fixes.
- **Least confident:** Whether blocking calls will work reliably with streamable HTTP transport under load. stdio is battle-tested for blocking, but streamable HTTP + 90-second tool calls may hit timeout issues in some clients. Need to verify during testing.
