---
title: "feat: MCP Server for Research Agent (Cycle 19)"
type: feat
status: active
date: 2026-02-28
origin: docs/brainstorms/2026-02-28-cycle-19-mcp-server-brainstorm.md
deepened: 2026-02-28
feed_forward:
  risk: "Whether blocking calls will work reliably with streamable HTTP transport under load. stdio is battle-tested for blocking, but streamable HTTP + 90-second tool calls may hit timeout issues in some clients."
  verify_first: true
---

# feat: MCP Server for Research Agent (Cycle 19)

## Enhancement Summary

**Deepened on:** 2026-02-28
**Research agents used:** kieran-python-reviewer, security-sentinel, performance-oracle, architecture-strategist, agent-native-reviewer, code-simplicity-reviewer, pattern-recognition-specialist, best-practices-researcher, learnings-researcher

### Key Improvements
1. **Added `list_contexts` tool** — agent-native reviewer found the `context` parameter on `run_research` is unusable without a discovery tool (CRITICAL gap)
2. **Fixed architectural layering** — extracting shared code (`REPORTS_DIR`, `get_auto_save_path`) from `cli.py` to a new `report_store.py`, eliminating the mcp→cli dependency flagged by 3 reviewers
3. **Corrected test regression scope** — actual count is 57 references (not 81): test_main.py has 0 (not 20), test_agent.py has 42 (not 46), test_coverage.py has 0 (not 2)
4. **Added security hardening** — `.md` extension whitelist, null byte rejection, query length limit, filename character whitelist, HTTP binding warning
5. **Adopted FastMCP patterns** — `ToolError` for errors, `mcp.test_client()` for testing, `"http"` transport string, sync `def` for non-async tools
6. **Restructured to 3 sessions** — merged print-to-logging (production + tests) into one session, keeping test suite green after each file

### Corrections to Original Plan
- Test count: 57 references (not 81) — test_main.py: 0, test_agent.py: 42, test_synthesize.py: 15, test_coverage.py: 0
- Transport string: `"http"` (fastmcp uses `"http"`, not `"streamable-http"`)
- Dependency: `fastmcp>=2.0,<4.0` (not `mcp>=1.26.0`)
- Tools: 5 (not 4) — added `list_contexts`
- `load_dotenv()` must be inside `main()`, not at module level
- Non-async tools should use sync `def`, not `async def`

## Prior Phase Risk

> **Least confident:** "Whether blocking calls will work reliably with streamable HTTP transport under load. stdio is battle-tested for blocking, but streamable HTTP + 90-second tool calls may hit timeout issues in some clients. Need to verify during testing."

This plan addresses this by including an integration test for streamable HTTP with a simulated long-running tool call (Session 3). If timeout issues surface, the HTTP transport can be documented as experimental in this cycle.

## Overview

Add an MCP (Model Context Protocol) server that wraps the research agent's existing async API, letting any MCP-compatible client (Claude Code, Cursor, Claude Desktop) run research queries, browse saved reports, discover contexts, and check available modes — without touching the CLI.

The agent is already pip-installable (v0.18.0). The public async API (`run_research_async`) is MCP-ready. This cycle adds a thin MCP layer on top, after fixing stdout contamination that would break the stdio transport.

## Problem Statement / Motivation

The research agent is CLI-only. Users who work inside Claude Code, Cursor, or Claude Desktop can't use it without leaving their editor to run terminal commands. MCP is the dominant protocol for LLM tool access — adopted by Anthropic, OpenAI, Google DeepMind, and Microsoft. Building an MCP server gives integration with all MCP-compatible clients for free.

(see brainstorm: docs/brainstorms/2026-02-28-cycle-19-mcp-server-brainstorm.md — "Why This Approach" section)

## Proposed Solution

### Architecture

```
research_agent/
├── mcp_server.py    ← NEW: thin MCP wrapper (~120-140 lines)
├── report_store.py  ← NEW: extracted from cli.py (~30 lines)
├── __init__.py      ← existing public API (unchanged)
├── agent.py         ← FIX: 43 print() → logging (stdout contamination)
├── relevance.py     ← FIX: 3 print() → logging
├── synthesize.py    ← FIX: 10 print() → logging/stderr
├── cli.py           ← REFACTOR: extract shared code + add logging config
└── ...              ← all other modules unchanged
```

### Five Tools (Intent-Based)

| Tool | Wraps | Parameters | Sync/Async |
|------|-------|------------|------------|
| `run_research` | `run_research_async()` | `query` (required), `mode` (optional), `context` (optional) | `async def` |
| `list_saved_reports` | `get_reports()` | none | `def` (sync) |
| `get_report` | reads from `reports/` dir | `filename` (required) | `def` (sync) |
| `list_research_modes` | `list_modes()` | none | `def` (sync) |
| `list_contexts` | `list_available_contexts()` | none | `def` (sync) |

(see brainstorm: "Tool Design: Coarse Intent-Based" — rejected hybrid design with separate search/fetch/synthesize tools)

#### Research Insights: Tool Design

**Why `list_contexts` is critical (agent-native reviewer):** The `run_research` tool accepts an optional `context` parameter, but without a discovery tool, an MCP-connected agent has no way to know what context values are valid. `list_available_contexts()` already exists in the public API and is exported in `__init__.py`. Without this tool, the context parameter is effectively dead for MCP clients.

**Why sync `def` for non-async tools (python reviewer):** `list_saved_reports`, `get_report`, `list_contexts`, and `list_research_modes` do no async I/O. Declaring them `async` is misleading. FastMCP supports both sync and async tool functions — use plain `def` for tools that do no awaitable work.

**Intentionally omitted parameters (python reviewer):** `skip_critique` and `max_sources` are not exposed on `run_research`. These are power-user knobs: quick mode already skips critique, and modes have good default source counts. Can add later if needed.

**Expected durations in docstring (agent-native reviewer):** Include "Expected duration: quick ~10-20s, standard ~30-60s, deep ~90-180s" in the `run_research` docstring so calling LLMs can set user expectations.

**Tool count stays within best practice range (best-practices researcher):** LLM tool selection accuracy degrades past ~15 tools and "virtually guaranteed to fail" past 100. Our 5 tools are well within the reliable range. The 80/20 rule: 5 intent-based tools cover 100% of user workflows.

**Escape hatch trigger (architecture strategist):** If a downstream agent needs to decompose a query without executing research, or search without synthesizing, add standalone tools in a future cycle. The `__init__.py` API already exports the building blocks.

### Two Transports

- **stdio** (default) — for Claude Code / Cursor / Claude Desktop
- **streamable HTTP** — for remote/multi-client deployment
- Selected via `MCP_TRANSPORT` env var, defaults to `stdio`
- SSE is deprecated (MCP spec 2025-03-26), not supported

(see brainstorm: "Transport: Both (stdio + streamable HTTP)")

#### Research Insights: Transport

**Transport string correction (best-practices researcher):** The `fastmcp` package uses `"http"` as the transport string. Using `"streamable-http"` (which the `mcp` SDK used) would fail.

**Validate transport input (python reviewer):** Any value other than `"http"` or `"stdio"` should produce an error, not silently fall through to stdio. Add explicit validation with a clear error message.

**HTTP concurrent request limitation (performance oracle):** Shared mutable state in `fetch.py` (`_dns_cache`) and `search.py` (`_tavily_client`) makes concurrent HTTP requests unsafe. For MVP, document that HTTP transport does not support concurrent research runs. stdio is inherently serial and safe.

### SDK

`fastmcp` package v2.x+ (standalone FastMCP package). Import: `from fastmcp import FastMCP`. Decorator-based tool registration with auto-generated schemas from type annotations.

#### Research Insights: SDK Patterns

**FastMCP `instructions` parameter (agent-native reviewer):** Use it to inject CWD requirement info into the server description, so connected LLMs get context automatically:
```python
mcp = FastMCP(
    "Research Agent",
    instructions="Reports and contexts are relative to the working directory. "
    "Set 'cwd' in your MCP client config to the research-agent project root."
)
```

**FastMCP `ToolError` for errors (best-practices researcher):** Instead of returning error strings manually, raise `ToolError` from `fastmcp.exceptions`. FastMCP catches it and returns a `CallToolResult` with `isError=True`. The server stays running.

**Lifespan pattern deferred (best-practices researcher):** FastMCP supports `@asynccontextmanager` for shared resources (HTTP clients, DB pools). Not needed for MVP since each research run creates its own clients. Consider for a future cycle if client reuse becomes a performance concern.

## Technical Considerations

### Blocker: stdout Contamination (CRITICAL)

**Scope correction from brainstorm:** The brainstorm identified only `synthesize.py`, but SpecFlow analysis found **56 print() calls** across three files in the `run_research_async()` call path:

| File | print() count | Purpose |
|------|--------------|---------|
| `agent.py` | 43 | Progress messages (`[1/7] Searching...`), sub-query status, cascade recovery, gap info, skeptic results |
| `synthesize.py` | 10 | Report streaming (`print(text, end="", flush=True)`), disclaimers, newlines |
| `relevance.py` | 3 | Source scoring output |

**ALL** of these corrupt MCP's stdio transport. Every single one must be converted.

**Approach:**
- `agent.py` + `relevance.py`: Convert `print()` → `logger.info()` — these are progress/status messages where log formatting is fine
- `synthesize.py` streaming: Convert `print(text, end="", flush=True)` → `sys.stderr.write(text); sys.stderr.flush()` — preserves streaming UX without log-prefix artifacts on each chunk
- `synthesize.py` discrete: Convert `print(limited_disclaimer)` and `print()` → `sys.stderr.write()` — same rationale
- `cli.py`: Add logging configuration at `main()` startup — `StreamHandler(sys.stderr)` with `Formatter("%(message)s")`, level `INFO`

#### Research Insights: stdout Safety

**The cardinal rule (best-practices researcher):** The stdio transport uses stdout exclusively for JSON-RPC messages. ANY non-protocol bytes on stdout corrupt the stream and crash the connection. This is the single most common cause of MCP server failures.

**Check third-party libraries (best-practices researcher):** Beyond our own print() calls, verify that no imported library prints to stdout on import. If found, redirect stdout during import:
```python
import sys, io
_real_stdout = sys.stdout
sys.stdout = io.StringIO()
try:
    import noisy_library
finally:
    sys.stdout = _real_stdout
```

**Stepping stone, not final architecture (architecture strategist, learnings):** The print-to-logging conversion blocks MCP progress reporting (`ctx.report_progress()`) and multi-tenant HTTP deployment. A future cycle should implement the callback architecture described in `docs/solutions/architecture/agent-native-return-structured-data.md`. Document this explicitly so future developers don't treat logging as the permanent solution.

**Comment in synthesize.py (architecture strategist):** The streaming chunks use `sys.stderr.write()` while discrete messages use `logger`. Document why in a code comment — two different output mechanisms in one file needs explanation.

**Corrected test regression count (simplicity reviewer, verified by grep):**

| File | Actual `builtins.print` mocks | Plan originally claimed |
|------|------|------|
| `test_agent.py` | **42** | ~~46~~ |
| `test_synthesize.py` | 15 | 15 |
| `test_main.py` | **0** | ~~20~~ |
| `test_coverage.py` | **0** | ~~not mentioned~~ |
| **Total** | **57** | ~~81~~ |

### Brainstorm Correction: No Cache Leak

The brainstorm says `_context_cache` in `context.py` is an unbounded memory leak. **SpecFlow analysis found this is not the case.** The current code uses per-run caches via `new_context_cache()` (`context.py:126`). Each `ResearchAgent` run creates a fresh `dict` that's garbage-collected when the run completes. There is no module-level unbounded cache.

**Decision:** Skip the cache bounding fix. The leak doesn't exist in the current code.

### Architectural Fix: Extract Shared Code from `cli.py`

**Flagged by:** python reviewer (CRITICAL), architecture strategist, pattern specialist

The plan originally imported `get_auto_save_path` and `REPORTS_DIR` from `cli.py` into `mcp_server.py`. This creates a dependency from the MCP server to the CLI module — a layering violation. Both are "presentation layer" peers that should depend on the library, not on each other.

**Fix:** Extract shared utilities into `research_agent/report_store.py`:

```python
"""Report storage utilities shared by CLI and MCP server."""

import re
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path("reports")

def sanitize_filename(query: str, max_length: int = 50) -> str:
    # ... (moved from cli.py)

def get_auto_save_path(query: str) -> Path:
    # ... (moved from cli.py)
```

Both `cli.py` and `mcp_server.py` import from `report_store.py`. `__init__.py` re-exports `get_reports` as before (but `get_reports` also moves to `report_store.py`).

### Path Traversal Defense for `get_report`

The `get_report` tool reads files by user-supplied filename. Without validation, `../../.env` could read API keys.

#### Research Insights: Security Hardening

**Four-layer defense (security sentinel):**

```python
def _validate_report_filename(filename: str) -> Path:
    """Validate and resolve a report filename, preventing path traversal."""
    # Layer 1: reject path-like characters
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise ValueError(f"Invalid filename: {filename!r}")

    # Layer 2: reject null bytes
    if "\x00" in filename:
        raise ValueError("Invalid filename: contains null byte")

    # Layer 3: extension whitelist (prevents reading .env or other files in reports/)
    if not filename.endswith(".md"):
        raise ValueError("Only .md report files can be retrieved")

    # Layer 4: resolve and verify containment
    path = (REPORTS_DIR / filename).resolve()
    if not path.is_relative_to(REPORTS_DIR.resolve()):
        raise ValueError("Filename resolves outside reports/ directory")

    if not path.exists():
        raise FileNotFoundError(f"Report not found: {filename}")

    return path
```

**Use same exception types as `resolve_context_path()` (pattern specialist):** `ValueError` for validation failures, `FileNotFoundError` for missing files. Consistent with existing codebase pattern.

**Filename character whitelist (security sentinel):** Additionally validate with `re.match(r'^[a-zA-Z0-9_\-\.]+$', filename)` to reject any unexpected characters.

### .env Loading

The CLI calls `load_dotenv()` at startup (`cli.py:152`). The MCP server must also call `load_dotenv()`, but **inside `main()`** (not at module level).

#### Research Insights: load_dotenv Placement

**Module-level is a testing hazard (python reviewer, pattern specialist):** `load_dotenv()` at module level executes on import. Any test that imports `mcp_server` would trigger `.env` loading as a side effect, polluting the test environment with real API keys. The CLI calls `load_dotenv()` inside `main()` — the MCP server should match this pattern.

### CWD Sensitivity

`REPORTS_DIR = Path("reports")` and `CONTEXTS_DIR = Path("contexts")` are relative paths. They resolve relative to the process CWD.

**Decision:** Document that users must set `cwd` in their MCP client config to point to the research-agent project root. Use FastMCP's `instructions` parameter to surface this requirement to connected LLMs.

#### Research Insights: CWD Safety

**Add startup sanity check (architecture strategist):** In `main()`, verify the working directory looks correct by checking for `pyproject.toml` or `research_agent/` directory. Log a warning to stderr if not found:
```python
if not Path("research_agent").is_dir():
    logger.warning("CWD does not appear to be the research-agent project root")
```

### Auto-Save Behavior

The CLI auto-saves reports for standard/deep modes. `run_research_async()` itself does NOT auto-save.

**Decision:** Auto-save for standard and deep modes in the MCP server, using shared utilities from `report_store.py`.

#### Research Insights: Auto-Save

**Research log omission is intentional (architecture strategist):** The CLI also calls `append_research_log()` after saving — the MCP server does NOT. This is a conscious decision: the research log is a CLI convenience feature, not a data integrity concern. Document this explicitly.

**Don't sanitize queries in MCP layer (learnings: non-idempotent-sanitization):** The pipeline has established sanitization boundaries. Adding `sanitize_content()` in the MCP layer would cause the double-encoding bug (`&` → `&amp;` → `&amp;amp;`). The MCP server is a transport layer, not a sanitization boundary.

### Result Serialization

`run_research` returns a `ResearchResult` dataclass. For MCP:
- Return the markdown report as the primary text content
- Include `mode`, `sources_used`, `status`, and `saved_to` (filename if auto-saved) as a summary header
- Omit `CritiqueResult` — internal quality metric, not useful to calling LLM

#### Research Insights: Structured Data

**Include critique pass/fail signal (agent-native reviewer):** While the full `CritiqueResult` is too detailed, including `critique_pass: true/false` gives the calling LLM a quality signal to decide whether to present the report or re-run. Two extra fields in the metadata header.

**Make save status explicit (agent-native reviewer):** For quick mode (not auto-saved), the header should say `Saved: (not auto-saved, use mode=standard to save)` so the agent knows it can't retrieve this report later.

### Error Handling at MCP Boundary

The codebase convention says "Never bare `except Exception`." However, a server boundary is precisely where a catch-all is appropriate.

#### Research Insights: Error Patterns

**Use `ToolError` from FastMCP (best-practices researcher):**
```python
from fastmcp.exceptions import ToolError

@mcp.tool
async def run_research(query: str, ...) -> str:
    try:
        result = await run_research_async(query, mode=mode, context=context)
        return format_result(result)
    except ResearchError as e:
        raise ToolError(str(e))  # Clean, actionable error
    except Exception:
        logger.exception("Unexpected error in run_research")
        # Don't expose raw exception message — may contain filesystem paths
        raise ToolError(
            "Research failed unexpectedly. Try again, or use a different mode/query. "
            "If the error persists, check that API keys are configured."
        )
```

**Two-layer pattern (python reviewer, pattern specialist):** Catch `ResearchError` first (known failures with good messages, including valid options like "Must be one of: deep, quick, standard"). Catch-all `Exception` as the outer boundary with a generic, actionable message.

**Sanitize catch-all errors (security sentinel):** Third-party exceptions may leak filesystem paths (e.g., `OSError` containing `/Users/alejandroguillen/...`). The catch-all should NOT include `{e}` in the client-facing message. Log the full traceback to stderr for debugging.

**Write error messages for LLMs (best-practices researcher):** Include actionable guidance: what to try instead, what to check. Bad: `"KeyError: 'id'"`. Good: `"The paper ID was not found. Try searching with list_saved_reports first."`

**Add code comment explaining catch-all (architecture strategist):** Future contributors will see the CLAUDE.md "never bare except Exception" convention and may "fix" it. A comment explaining why this is the correct exception handling for a server boundary prevents regression.

### Input Validation

#### Research Insights: Query Safety

**Add query length limit (security sentinel):** No upper bound on query length exists. A 100,000 character query would be passed to multiple Claude API calls, costing significant money. Add `MAX_QUERY_LENGTH = 2000` check at the MCP layer.

**Filename character whitelist (security sentinel):** For `get_report`, validate with `re.match(r'^[a-zA-Z0-9_\-\.]+$', filename)` in addition to the path traversal checks.

### Logging Configuration

Both transports log to stderr. Never configure a stdout handler. The MCP server configures `logging.basicConfig(stream=sys.stderr, level=logging.WARNING, format="%(levelname)s: %(name)s: %(message)s")`.

#### Research Insights: Logging

**Match CLI format (pattern specialist):** The CLI uses `format="%(levelname)s: %(name)s: %(message)s"`. The MCP server should use the same format for consistency.

**Add `logger = logging.getLogger(__name__)` (pattern specialist):** Every module in the codebase has this line. The plan's code skeleton was missing it.

**Consider `MCP_LOG_LEVEL` env var (python reviewer):** For debugging: `log_level = os.environ.get("MCP_LOG_LEVEL", "WARNING").upper()`. Documents that progress is intentionally suppressed in MCP mode.

### HTTP Transport Security

#### Research Insights: Network Safety

**Binding address warning (security sentinel):** When `MCP_HOST` is not `127.0.0.1` or `localhost`, log a warning: "MCP server binding to {host}:{port} — accessible on the network. No authentication is configured."

**No auth, no TLS, no rate limiting (security sentinel):** The MCP server has no authentication. Anyone who can reach the HTTP port can run research queries (consuming API credits), read all saved reports, and list configuration. Document that HTTP transport should only be used on trusted networks or behind a reverse proxy providing TLS and authentication.

**Port parsing (python reviewer):** `int(os.environ.get("MCP_PORT", "8000"))` can raise `ValueError` if set to a non-integer. Wrap in try/except with a clear error message.

### Long-Running Server Concerns

#### Research Insights: Performance

**`_dns_cache` shared mutable state (performance oracle, CRITICAL for HTTP):** `fetch.py:165` has a module-level `_dns_cache: dict[str, bool]` that persists across research runs in a long-running server. While it's cleared at the start of `fetch_urls()`, concurrent HTTP requests would race on the same dict — weakening SSRF protection. **Fix:** Convert to a per-call local dict inside `fetch_urls()`. Low effort, mechanical parameter threading. This should be a preparatory fix in Session 2.

**`_tavily_client` global singleton (performance oracle):** `search.py:29` caches a `TavilyClient` globally. For stdio (serial requests), this is safe. For HTTP concurrent requests, it may not be thread-safe. **For MVP:** Document that concurrent HTTP requests are not supported. Consider removing the global cache in a future cycle.

**Memory profile (performance oracle):** Per-run allocations (~60MB for deep mode with 12 pages) are GC'd after each run. Server RSS stabilizes at 200-300MB after several runs. Acceptable for a developer workstation tool.

## Acceptance Criteria

- [ ] `research-agent-mcp` console script starts successfully with stdio transport (default)
- [ ] `research-agent-mcp` starts with `MCP_TRANSPORT=http` on `127.0.0.1:8000`
- [ ] `run_research` tool executes a query and returns a markdown report with metadata header
- [ ] `run_research` auto-saves reports for standard/deep modes, returns filename in metadata
- [ ] `run_research` rejects queries over 2000 characters with a clear error
- [ ] `list_saved_reports` returns saved reports with dates and query names
- [ ] `get_report` retrieves a saved report by filename, rejects path traversal attempts and non-.md files
- [ ] `list_research_modes` returns all three modes with cost estimates
- [ ] `list_contexts` returns available context files with previews
- [ ] All errors use `ToolError` with actionable, LLM-readable messages
- [ ] Zero `print()` calls remain in `run_research_async()` call path
- [ ] All 769 existing tests pass after print-to-logging conversion
- [ ] New MCP server tests use `mcp.test_client()` and cover all tools + error paths
- [ ] `.env` loading works (API keys found when `.env` file exists)

## Dependencies & Risks

**New dependency:** `fastmcp>=2.0,<4.0` added to `pyproject.toml`. Requires Python >=3.10 (already our minimum). Verify no conflicts with existing deps (`anthropic`, `httpx`, `httpcore`).

**Risk: Test regression size.** 57 test references to print() must be updated (corrected from 81). This is mechanical but error-prone. Converting each file's production code + tests together keeps the suite green throughout.

**Risk: Streaming UX change.** Converting synthesize.py's `print()` to `sys.stderr.write()` changes where streaming output appears (stdout → stderr). For terminal users, this is invisible (both go to the terminal). For users piping stdout, this is a behavior change. Document in release notes.

**Risk: HTTP transport timeouts.** Deep-mode queries can take 2-3 minutes (`SYNTHESIS_TIMEOUT` alone is 120s). Some MCP clients may time out. Mitigated by: (a) expected durations in tool docstring, (b) integration test with simulated long call, (c) documenting proxy timeout requirements (`proxy_read_timeout 300s`).

**Risk: HTTP concurrent requests unsafe.** Module-level mutable state (`_dns_cache`, `_tavily_client`) makes concurrent HTTP requests unsafe. Mitigated by: documenting single-concurrency limitation for HTTP, fixing `_dns_cache` to per-call in Session 2.

## Implementation Plan

### Session 1: Print-to-Logging Conversion (Production + Tests Together)

**Goal:** Eliminate all `print()` calls from the `run_research_async()` call path. Keep test suite green after each file.

**Approach:** Convert each file's print() calls AND its corresponding test mocks together, then run tests. This prevents the broken-intermediate-state problem of doing all production code first.

**Step 1: `agent.py` + `test_agent.py`**
- `research_agent/agent.py` — 43 `print()` → `logger.info()` (agent.py already has `logger = logging.getLogger(__name__)`)
- `tests/test_agent.py` — 42 references: change `mock.patch("builtins.print")` → assert on logger or remove print assertions
- Run `pytest tests/test_agent.py -v` — must pass

**Step 2: `synthesize.py` + `test_synthesize.py`**
- `research_agent/synthesize.py` — 10 `print()` → `sys.stderr.write()` / `sys.stderr.flush()` (streaming chunks and discrete messages)
- Add code comment explaining why stderr.write (not logger) for streaming chunks
- `tests/test_synthesize.py` — 15 references: change print mocks to stderr write mocks
- Run `pytest tests/test_synthesize.py -v` — must pass

**Step 3: `relevance.py` + CLI logging**
- `research_agent/relevance.py` — 3 `print()` → `logger.info()`
- `research_agent/cli.py` — Add logging configuration at `main()` startup:
  ```python
  handler = logging.StreamHandler(sys.stderr)
  handler.setFormatter(logging.Formatter("%(message)s"))
  logging.getLogger("research_agent").addHandler(handler)
  logging.getLogger("research_agent").setLevel(logging.INFO)
  ```
- Run full `pytest tests/ -v` — all 769 tests must pass

**Estimated changes:** ~200-250 lines (production + tests combined)
**Commits:** One per step (~3 commits)

### Session 2: MCP Server Implementation

**Goal:** Create `report_store.py`, `mcp_server.py`, and update `pyproject.toml` + `cli.py`.

**Step 1: Extract `report_store.py` from `cli.py`**

Action items:
- Move `REPORTS_DIR`, `sanitize_filename`, `get_auto_save_path`, and `get_reports` from `cli.py` to new `research_agent/report_store.py`
- Update `cli.py` to import from `report_store`
- **Update `__init__.py`**: change `from .cli import get_reports` to `from .report_store import get_reports` — this re-export must point to the new module or the public API breaks

Run `pytest tests/ -v` — all tests must still pass.

**Step 2: Fix `_dns_cache` in `fetch.py`** (separate concern — MCP server safety prep)

- Convert `_dns_cache` module-level dict in `fetch.py` to a per-call local dict inside `fetch_urls()`
- Thread the local dict through any internal functions that reference it

Run `pytest tests/ -v` — all tests must still pass.

**Step 3: Create `mcp_server.py` (~120-140 lines)**

```python
"""MCP server for the research agent."""

import logging
import os
import re
import sys
from pathlib import Path

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

MAX_QUERY_LENGTH = 2000

mcp = FastMCP(
    "Research Agent",
    instructions=(
        "Research agent that searches the web and generates structured markdown reports. "
        "Reports and contexts are relative to the working directory. "
        "Set 'cwd' in your MCP client config to the research-agent project root."
    ),
)


@mcp.tool
async def run_research(
    query: str,
    mode: str = "standard",
    context: str | None = None,
) -> str:
    """Run a research query and get a structured markdown report.

    Expected duration: quick ~10-20s, standard ~30-60s, deep ~90-180s.

    Args:
        query: The research question to investigate.
        mode: Research depth — "quick" (4 sources, ~$0.12),
              "standard" (10 sources, ~$0.35), or "deep" (12 sources, 2-pass, ~$0.85).
        context: Three-way behavior:
                 - Omit (default None): auto-detect context from contexts/ dir
                   (costs 1 extra API call to scan available files).
                 - "none" (string): skip context loading entirely — no extra API call.
                 - "<name>" (e.g., "pfe"): load a specific context file from contexts/<name>.yaml.
                 Use list_contexts to see available names.
    """
    from fastmcp.exceptions import ToolError
    from research_agent import ResearchError, run_research_async
    from research_agent.report_store import get_auto_save_path, REPORTS_DIR
    from research_agent.safe_io import atomic_write
    from research_agent.errors import StateError

    if len(query) > MAX_QUERY_LENGTH:
        raise ToolError(
            f"Query too long ({len(query)} chars, max {MAX_QUERY_LENGTH}). "
            "Shorten your query and try again."
        )

    try:
        result = await run_research_async(query, mode=mode, context=context)
    except ResearchError as e:
        # Strip absolute filesystem paths to avoid leaking server directory structure
        msg = re.sub(r'(/Users/|/home/)\S+', '<path>', str(e))
        raise ToolError(msg)
    except Exception:
        logger.exception("Unexpected error in run_research")
        # Server boundary catch-all. Don't expose raw exception message
        # (may contain filesystem paths from third-party libs).
        # See CLAUDE.md: "Never bare except Exception" — this is the one
        # justified exception: an MCP server boundary where unhandled errors
        # would crash the entire server process.
        raise ToolError(
            "Research failed unexpectedly. Try again, or use a different mode/query. "
            "If the error persists, check that API keys are configured."
        )

    # Auto-save for standard/deep modes
    saved_to = None
    if result.mode in ("standard", "deep"):
        try:
            save_path = get_auto_save_path(query)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(save_path, result.report)
            saved_to = save_path.name
        except (OSError, StateError) as e:
            logger.warning("Auto-save failed: %s", e)

    # Format metadata header
    save_info = saved_to or "(not auto-saved, use mode=standard to save)"
    header = (
        f"Mode: {result.mode} | Sources: {result.sources_used} | "
        f"Status: {result.status} | Saved: {save_info}"
    )
    return f"{header}\n\n{result.report}"


@mcp.tool
def list_saved_reports() -> str:
    """List all saved research reports with dates and query names.

    Returns a formatted list of reports available for retrieval via get_report.
    """
    from research_agent import get_reports

    reports = get_reports()
    if not reports:
        return "No saved reports found. Run research in standard or deep mode to auto-save."
    lines = []
    for r in reports:
        date_str = r.date or "unknown date"
        lines.append(f"- {r.filename} ({date_str}: {r.query_name})")
    return "\n".join(lines)


@mcp.tool
def get_report(filename: str) -> str:
    """Retrieve a saved research report by filename.

    Args:
        filename: Report filename (e.g., "query_name_2026-02-28_143052.md").
                  Use list_saved_reports to see available files.
    """
    from fastmcp.exceptions import ToolError
    from research_agent.report_store import REPORTS_DIR

    try:
        path = _validate_report_filename(filename)
    except (ValueError, FileNotFoundError) as e:
        raise ToolError(str(e))
    return path.read_text()


@mcp.tool
def list_research_modes() -> str:
    """Show available research modes and their configurations."""
    from research_agent import list_modes

    modes = list_modes()
    lines = []
    for m in modes:
        save_str = "auto-saves" if m.auto_save else "no auto-save"
        lines.append(
            f"- {m.name}: {m.max_sources} sources, ~{m.word_target} words, "
            f"{m.cost_estimate}, {save_str}"
        )
    return "\n".join(lines)


@mcp.tool
def list_contexts() -> str:
    """List available research context files and their descriptions.

    Use context names as the 'context' parameter in run_research.
    """
    from research_agent import list_available_contexts

    contexts = list_available_contexts()
    if not contexts:
        return "No context files found in contexts/ directory."
    lines = []
    for name, preview in contexts:
        lines.append(f"- {name}: {preview[:100]}")
    return "\n".join(lines)


def _validate_report_filename(filename: str) -> Path:
    """Validate and resolve a report filename, preventing path traversal."""
    from research_agent.report_store import REPORTS_DIR

    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise ValueError(f"Invalid filename: {filename!r}")
    if "\x00" in filename:
        raise ValueError("Invalid filename: contains null byte")
    if len(filename) > 255:
        raise ValueError(f"Filename too long: {len(filename)} characters")
    if not filename.endswith(".md"):
        raise ValueError("Only .md report files can be retrieved")
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
        raise ValueError(f"Invalid filename characters: {filename!r}")
    path = (REPORTS_DIR / filename).resolve()
    if not path.is_relative_to(REPORTS_DIR.resolve()):
        raise ValueError("Filename resolves outside reports/ directory")
    if not path.exists():
        raise FileNotFoundError(f"Report not found: {filename}")
    return path


def main():
    """Entry point for the research-agent-mcp console script."""
    from dotenv import load_dotenv

    load_dotenv()

    log_level = os.environ.get("MCP_LOG_LEVEL", "WARNING").upper()
    logging.basicConfig(
        stream=sys.stderr,
        level=getattr(logging, log_level, logging.WARNING),
        format="%(levelname)s: %(name)s: %(message)s",
    )

    # CWD sanity check
    if not Path("research_agent").is_dir() and not Path("pyproject.toml").exists():
        logger.warning(
            "CWD does not appear to be the research-agent project root. "
            "Set 'cwd' in your MCP client config."
        )

    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()

    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "http":
        host = os.environ.get("MCP_HOST", "127.0.0.1")
        try:
            port = int(os.environ.get("MCP_PORT", "8000"))
        except ValueError:
            sys.exit(f"MCP_PORT must be an integer, got: {os.environ['MCP_PORT']!r}")

        if host not in ("127.0.0.1", "localhost"):
            logger.warning(
                "MCP server binding to %s:%d — accessible on the network. "
                "No authentication is configured.", host, port,
            )

        # host/port go in FastMCP constructor, not run(). run() only accepts transport.
        # Reconfigure the module-level mcp object before starting.
        mcp.settings.host = host
        mcp.settings.port = port
        mcp.run(transport="http")
    else:
        sys.exit(f"Unknown MCP_TRANSPORT: {transport!r}. Use 'stdio' or 'http'.")


if __name__ == "__main__":
    main()
```

**Step 4: Update `pyproject.toml`**
- Add `"fastmcp>=2.0,<4.0"` to `dependencies`
- Add `research-agent-mcp = "research_agent.mcp_server:main"` to `[project.scripts]`
- Add `asyncio_mode = "auto"` under `[tool.pytest.ini_options]` (eliminates `@pytest.mark.asyncio` boilerplate for Session 3 tests)

**Estimated changes:** ~200 lines (new files + pyproject.toml + cli.py refactor + fetch.py fix)
**Commits:** One per step (~4 commits)

### Session 3: MCP Server Tests

**Preamble:** Run `pip install -e ".[test]"` to pick up the `fastmcp` dependency added to `pyproject.toml` in Session 2.

**Goal:** Test all 5 tools, both transports, and error paths.

**New file: `tests/test_mcp_server.py` (~200-250 lines)**

#### Research Insights: Testing Patterns

**Use `mcp.test_client()` (best-practices researcher):** FastMCP provides an in-memory test client that avoids subprocess overhead entirely:

```python
import pytest
from research_agent.mcp_server import mcp

@pytest.fixture
async def client():
    async with mcp.test_client() as client:
        yield client

@pytest.mark.asyncio
async def test_list_modes(client):
    result = await client.call_tool("list_research_modes", arguments={})
    assert not result.isError
    # Verify all three modes are listed
```

**Set `asyncio_mode = "auto"` in pyproject.toml (best-practices researcher):** Eliminates the need for `@pytest.mark.asyncio` on every test.

Tests to write:
- **Unit tests (in-memory client, mocked pipeline):**
  - `run_research` with valid query returns report + metadata header
  - `run_research` with invalid mode returns ToolError with valid options
  - `run_research` with empty query returns ToolError
  - `run_research` with missing API keys returns ToolError
  - `run_research` with query over 2000 chars returns ToolError
  - `run_research` auto-saves for standard mode, not for quick
  - `run_research` metadata includes saved_to filename
  - `list_saved_reports` with reports returns formatted list
  - `list_saved_reports` with empty dir returns helpful message
  - `get_report` with valid filename returns file content
  - `get_report` with path traversal (`../../.env`) returns ToolError
  - `get_report` with non-.md file returns ToolError
  - `get_report` with null byte returns ToolError
  - `get_report` with nonexistent file returns ToolError
  - `list_research_modes` returns all three modes with cost estimates
  - `list_contexts` with contexts returns names + previews
  - `list_contexts` with no contexts dir returns helpful message
  - Unhandled exception in pipeline returns clean ToolError (catch-all test)
  - Catch-all error does NOT leak filesystem paths

- **Integration tests:**
  - stdio roundtrip: start server subprocess, send MCP request via stdin, assert valid response on stdout
  - HTTP roundtrip: start server in fixture, send HTTP request to `/mcp`, assert valid response

- **Transport validation test:**
  - `MCP_TRANSPORT=invalid` produces an error exit

**Estimated changes:** ~250 lines

## Sources & References

### Origin

- **Brainstorm document:** [docs/brainstorms/2026-02-28-cycle-19-mcp-server-brainstorm.md](docs/brainstorms/2026-02-28-cycle-19-mcp-server-brainstorm.md) — Key decisions carried forward: 5 coarse tools (4 from brainstorm + list_contexts), both transports, blocking execution, FastMCP decorator pattern.

### Internal References

- Public API: `research_agent/__init__.py` — `run_research_async()`, `list_modes()`, `get_reports()`, `list_available_contexts()`
- Path traversal defense pattern: `research_agent/context.py:151-163` — `resolve_context_path()`
- Auto-save logic: `research_agent/cli.py:71-76` — `get_auto_save_path()` (moving to `report_store.py`)
- Result types: `research_agent/results.py` — `ResearchResult`, `ModeInfo`, `ReportInfo`

### Institutional Learnings Applied

- `docs/solutions/architecture/agent-native-return-structured-data.md` — return structured data, not strings. Applied: metadata header on run_research response
- `docs/solutions/architecture/pip-installable-package-and-public-api.md` — validation ownership in data-owning module. Applied: delegate all validation to existing functions
- `docs/solutions/security/context-path-traversal-defense-and-sanitization.md` — two-layer path defense. Applied: same pattern for get_report
- `docs/solutions/security/non-idempotent-sanitization-double-encode.md` — don't sanitize in MCP layer. Applied: pass raw queries to pipeline
- `docs/solutions/architecture/domain-agnostic-pipeline-design.md` — explicit None over hidden defaults. Applied: context param defaults to None
- `docs/solutions/logic-errors/dead-catch-and-narrow-httpx-exceptions.md` — catch parent exceptions, not individual subclasses. Applied: catch ResearchError broadly

### External References

- [FastMCP (PyPI)](https://pypi.org/project/fastmcp/) — v2.x+, `from fastmcp import FastMCP`
- [FastMCP Running Guide](https://gofastmcp.com/deployment/running-server) — stdio/HTTP transport patterns
- [FastMCP Testing](https://gofastmcp.com/patterns/testing) — `mcp.test_client()` pattern
- [FastMCP Error Handling](https://gofastmcp.com/python-sdk/fastmcp-server-middleware-error_handling) — `ToolError` pattern
- [Speakeasy — Why Less Is More for MCP](https://www.speakeasy.com/mcp/tool-design/less-is-more) — tool count best practices
- [gptr-mcp (GPT Researcher)](https://github.com/assafelovic/gptr-mcp) — coarse tool design reference
- Master roadmap: `docs/research/master-recommendations-future-cycles.md` (Cycle 19 section)

### Reference Implementations

| Project | Pattern | Takeaway |
|---------|---------|----------|
| gptr-mcp | 5 coarse tools over complex pipeline | Our model — few tools, LLM doesn't orchestrate |
| arxiv-mcp-server | Modular tools/ directory, clean separation | Good structure reference for future growth |
| Firecrawl MCP | 12 tools + async job pair | Async useful later, not needed yet |

## Optional: Consider for This Cycle or Next

These are low-effort additions that reuse existing infrastructure. Not required for MVP but worth considering if time allows in Session 2 or a follow-up cycle.

- **`delete_report(filename)` tool** (~10 lines) — Reuses `_validate_report_filename()` for path safety, then calls `path.unlink()`. Gives MCP clients the ability to clean up old reports without shell access.
- **`critique_report(filename)` tool** (~20 lines) — Wraps the already-exported `critique_report_file()` from `__init__.py`. Lets an agent request a quality check on a saved report and decide whether to re-run the research.
- **Improve `list_saved_reports` return format** — Current format (`- filename (date: query_name)`) is human-readable but hard for LLMs to parse programmatically. Consider returning structured lines like `filename | date | query_name` or a simple table, so calling agents can reliably extract filenames for `get_report` calls.

## Feed-Forward

- **Hardest decision:** Balancing simplicity-reviewer's "drop HTTP transport" recommendation against the brainstorm's explicit "both transports" decision. Kept HTTP but with full safety hardening (binding warning, port validation, transport validation, documented limitations). The brainstorm made this decision with full context — overriding it in planning feels like second-guessing a reasoned choice.
- **Rejected alternatives:** (1) Callback-based streaming — cleaner long-term but requires changing 3 synthesis function signatures, larger refactor than print→stderr. Save for a future cycle. (2) `RESEARCH_AGENT_HOME` env var for CWD — overengineering for MVP. (3) Cache bounding fix — leak doesn't exist. (4) Module-level `load_dotenv()` — testing hazard, moved to `main()`. (5) `async def` for non-async tools — misleading, changed to sync `def`. (6) Dropping auto-save — creates tool inconsistency (list_reports can't find MCP-generated reports).
- **Least confident:** ~~(Resolved)~~ The dependency is `fastmcp>=2.0,<4.0` (standalone package), not the `mcp` SDK. Import paths confirmed: `from fastmcp import FastMCP`, `from fastmcp.exceptions import ToolError`. `mcp.test_client()` exists. Remaining uncertainty: whether `mcp.settings.host`/`mcp.settings.port` reconfiguration works reliably before `run()` for HTTP transport — verify during Session 2 implementation.
