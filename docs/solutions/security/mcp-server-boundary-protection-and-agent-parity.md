---
title: MCP Server Boundary Protection — Security, Agent Parity, and LLM Input Normalization
slug: mcp-server-boundary-protection-and-agent-parity
category: security
tags:
  - mcp-server
  - trust-boundary
  - input-normalization
  - agent-parity
  - llm-callers
  - localhost
severity: P1
components:
  - research_agent/mcp_server.py
  - research_agent/agent.py
  - tests/test_mcp_server.py
  - pyproject.toml
date: 2026-02-28
cycle: 19
related_findings:
  - "089"
  - "090"
  - "091"
  - "092"
  - "093"
  - "094"
  - "095"
  - "096"
  - "097"
  - "098"
  - "099"
---

# MCP Server Boundary Protection and Agent Parity

## Core Insight

When wrapping a CLI tool as an MCP server, the trust model shifts from "local user on the same machine" to "potentially untrusted LLM client over HTTP." This shift creates three categories of issues that must be addressed at the MCP boundary layer — not deeper in the pipeline:

1. **Transport security** — who can connect and what leaks in errors
2. **Agent parity** — every CLI capability must be reachable via MCP tools
3. **Input normalization** — LLM clients send non-deterministic type representations

---

## Pattern 1: MCP Server Boundary Security

### The Problem

Two boundary leaks in the HTTP transport:

**089 (P1) — Non-localhost binding.** The original code issued a `logger.warning()` for non-loopback `MCP_HOST`, then started the server anyway. No authentication exists on FastMCP's HTTP transport, so any network process could invoke all tools and read environment variables including `ANTHROPIC_API_KEY` and `TAVILY_API_KEY`. The allowed set also missed `::1` (IPv6 loopback).

**090 (P2) — Path leakage in errors.** The `except ResearchError` handler stripped filesystem paths before raising `ToolError`, but the regex `/Users/|/home/` only matched macOS and Linux home directories. Paths under `/opt/`, `/var/`, `/tmp/` leaked server directory structure to MCP clients.

### The Solution

**089 — Hard exit on non-loopback binding:**

```python
if host not in ("127.0.0.1", "localhost", "::1"):
    sys.exit(
        f"Refusing to bind MCP HTTP server to {host}:{port} — "
        "no authentication is configured. Binding to a non-loopback "
        "address would expose all tools (and API keys) to the network.\n"
        "Options:\n"
        "  1. Use MCP_HOST=127.0.0.1 (default) for local-only access\n"
        "  2. Use MCP_TRANSPORT=stdio for production deployments\n"
        "  3. Place a reverse proxy with auth in front of localhost"
    )
```

The allowed set is `{"127.0.0.1", "localhost", "::1"}` — the third entry covers dual-stack hosts.

**090 — Broadened path-stripping regex:**

```python
msg = re.sub(r'(?<!:/)(?<!/)/(?:[\w.-]+/)+[\w.-]+', '<path>', str(e))
raise ToolError(msg)
```

The negative lookbehind `(?<!:/)(?<!/)` prevents matching URLs (`https://example.com/path` is skipped). The broader pattern catches any multi-segment Unix path.

### Why This Approach

**089:** Bearer token auth (`MCP_AUTH_TOKEN`) was rejected — FastMCP doesn't expose middleware hooks, so implementing it would require monkey-patching. Localhost-only eliminates the attack surface entirely without added complexity.

**090:** A simpler `/\S+` pattern was rejected because it would also strip URLs in error messages, destroying diagnostic information.

---

## Pattern 2: Agent-Native Parity Checklist

### The Problem

Three parity gaps between CLI and MCP:

- **093 (P2):** Invalid modes (e.g., `"fast"`) passed straight into the pipeline, failing deep inside with unhelpful errors instead of a clean `ToolError`.
- **094 (P2):** `critique_report_file()` was a public API with no MCP tool wrapper — clients couldn't evaluate report quality.
- **095 (P2):** `--skip-critique` and `--max-sources` CLI flags had no MCP equivalents.

### The Solution

**093 — `VALID_MODES` with early `ToolError`:**

```python
VALID_MODES = {"quick", "standard", "deep"}

if mode not in VALID_MODES:
    raise ToolError(
        f"Invalid mode: {mode!r}. Must be one of: {', '.join(sorted(VALID_MODES))}"
    )
```

**094 — `critique_report` tool wrapping public API:**

```python
@mcp.tool
def critique_report(filename: str) -> str:
    path = _validate_report_filename(filename)
    client = Anthropic()
    result = critique_report_file(client, path, model=DEFAULT_MODEL)
    # Format and return structured result
```

Reuses `_validate_report_filename` for path security — no separate traversal check needed.

**095 — Pass-through parameters:**

```python
async def run_research(
    query: str, mode: str = "standard", context: str | None = None,
    skip_critique: bool = False, max_sources: int | None = None,
) -> str:
```

### The Checklist

When wrapping a CLI as an MCP server, verify each item:

1. **All public API functions are reachable as tools.** If the CLI has `critique_report_file`, there must be a `critique_report` tool.
2. **All mode/enum parameters are validated at the MCP boundary.** Use a module-level constant (`VALID_MODES`) so the check is testable without mocking.
3. **All optional CLI flags exist as optional tool parameters.** Every `--flag` needs a default-valued MCP equivalent. Missing params force clients to use suboptimal defaults.
4. **Error types are translated.** Internal exceptions must become `ToolError` at the boundary. Raw exceptions crash the MCP server.
5. **Path security is centralized.** Any tool accepting a filename routes through a single `_validate_report_filename()`.
6. **The MCP `instructions` field mentions all available tools.** LLM clients use this for discovery before reading individual docstrings.

### Why This Approach

**093:** `Literal["quick", "standard", "deep"]` type annotation was rejected — not all MCP clients enforce schema types, so a runtime check is defense-in-depth.

**094:** The deferred import pattern (creating `Anthropic()` inside the tool function) is consistent with other tools and means tests mock the public API, not the constructor.

---

## Pattern 3: Defensive Input Normalization for LLM Callers

### The Problem

The `context` parameter has three-way behavior:

| Value | Meaning |
|-------|---------|
| `None` (Python null) | Auto-detect context from `contexts/` directory |
| `"none"` (the string) | Skip context loading entirely |
| `"<name>"` e.g. `"pfe"` | Load specific context file |

LLM clients frequently send wrong representations of "no value": `"null"` (JSON null stringified), `""` (empty string), or whitespace. These get interpreted as context file names, causing `FileNotFoundError` deep in the pipeline.

### The Solution

Three lines of normalization at the MCP boundary (`mcp_server.py`):

```python
if context is not None:
    context = context.strip()
    if context.lower() in ("null", ""):
        context = None
```

1. Guard: true Python `None` is already correct — don't touch it.
2. `strip()`: remove whitespace from template rendering artifacts.
3. Convert `"null"` and `""` to `None`. The string `"none"` is **not** in this check — it passes through as the skip-context sentinel.

### Why This Approach

**Normalizing `"None"` (capital N) was rejected.** In JSON-typed MCP calls, `null` arrives as Python `None`. The string `"None"` is a client bug — normalizing it would mask the bug. The common LLM mistake is `"null"` (lowercase JSON), which is covered.

**Rejecting with `ToolError` was rejected.** The correct behavior (null → auto-detect) is unambiguous, so graceful normalization costs nothing. A `ToolError` would interrupt the workflow and require the LLM to retry.

---

## Prevention Strategies

### Checklist for New MCP Servers

**Transport:**
- [ ] Server binds to `127.0.0.1` only, never `0.0.0.0`
- [ ] Non-loopback `--host` values are rejected at startup with `sys.exit()`
- [ ] For production, use `stdio` transport (eliminates HTTP surface entirely)

**Error Messages:**
- [ ] Every exception handler that surfaces messages strips filesystem paths
- [ ] Use a shared sanitization utility, not inline stripping per handler
- [ ] Boundary `except Exception` blocks must use `logger.exception()` and return a sanitized `ToolError` — never re-raise raw
- [ ] Test the stripping regex with: absolute paths, relative paths, paths inside strings, and URLs (negative test)

**Input Normalization:**
- [ ] String-but-optional fields: convert `"null"`, `""` to `None` at boundary
- [ ] Boolean fields: accept `"true"`/`"false"` as well as actual booleans
- [ ] Unbounded string inputs (query, filename) are length-capped at the MCP boundary
- [ ] Apply normalization in a single boundary function, not scattered per tool

**Tool Completeness:**
- [ ] Every CLI flag has an MCP parameter equivalent (or documented omission)
- [ ] Every public API function has an MCP tool wrapper
- [ ] Instructions field mentions all tools by name
- [ ] After adding/removing a tool, update instructions in the same commit

**Dependencies:**
- [ ] Pin to major version (`>=2.0,<3.0`), not open-ended (`>=2.0`)

### For MCP Server Reviews

1. Grep for `host=`, `bind=`, `listen(` — confirm no `0.0.0.0` or wildcard
2. Every `except` block that re-raises: confirm paths are stripped
3. Grep for `logger.` + `f"` on same line — flag f-string logger anti-pattern
4. Diff CLI flags vs MCP params — every gap needs justification
5. Check that mock assertions use `assert_called_once_with`, not bare `assert_called`

---

## Risk Resolution

### Path regex negative lookbehind (Batch 1)
- **Flagged:** Edge cases with paths embedded mid-sentence or in tracebacks
- **What happened:** Broadened regex caught more true positives; no false positives in test suite
- **Lesson:** When a security regex is flagged as potentially under-matching, add explicit negative tests (confirming non-path strings are unchanged). The test suite did not add these — the risk was accepted, not resolved.

### critique_report catch-all except Exception (Batch 2 → HANDOFF)
- **Flagged:** Broad `except Exception` at server boundary could swallow unexpected errors
- **What happened:** Remained through all 3 batches. Documented in HANDOFF as open risk.
- **Lesson:** Risks that survive a full cycle must be promoted from HANDOFF notes into formal todo items before the session closes. HANDOFF.md is ephemeral; the todo tracker is the source of truth for what gets worked next.

### Test count net +0 (Batch 3)
- **Flagged:** Removing 7 tests and adding 8 could mask coverage loss
- **What happened:** Unique tests were migrated before deletion, but no `pytest --cov` before/after diff was recorded.
- **Lesson:** Net-zero test count changes need coverage verification, not just count verification. Run coverage before and after, include the delta in the batch file.

---

## Related Documentation

- [context-path-traversal-defense-and-sanitization.md](context-path-traversal-defense-and-sanitization.md) — Two-layer path defense precedent for Finding 090
- [domain-matching-substring-bypass.md](domain-matching-substring-bypass.md) — New code paths inherit same threat model as primary path (Finding 089 context)
- [ssrf-bypass-via-proxy-services.md](ssrf-bypass-via-proxy-services.md) — Unauthenticated proxy path threat model
- [../architecture/agent-native-return-structured-data.md](../architecture/agent-native-return-structured-data.md) — Root cause of agent-parity gaps (Findings 094-095)
- [../architecture/pip-installable-package-and-public-api.md](../architecture/pip-installable-package-and-public-api.md) — Validation ownership pattern (Finding 093)
- [../logic-errors/defensive-yaml-frontmatter-parsing.md](../logic-errors/defensive-yaml-frontmatter-parsing.md) — Sanitize-at-boundary pattern extends to Finding 097

---

## Three Questions

1. **Hardest pattern to extract from the fixes?** The input normalization pattern (097). The three-way `None`/`"none"`/`"name"` behavior means normalization must be surgical — converting `"null"` to `None` while preserving `"none"` requires understanding the semantic difference between "I didn't provide a value" and "I explicitly chose to skip." This is not obvious from the code alone and required reading the batch docs to understand why `"None"` (capital N) was deliberately excluded.

2. **What did you consider documenting but left out, and why?** The f-string logger fix (091) and test assert gap (092). Both are straightforward code quality fixes with no reusable pattern — they're "remember to do this" items, not "here's how to solve this class of problem." They belong in a linting rule, not a solution doc.

3. **What might future sessions miss that this solution doesn't cover?** The downstream prompt injection surface. The review flagged that MCP clients are a new entry point where queries originate from potentially untrusted sources, but the existing three-layer defense (sanitize + XML boundaries + system prompt) was designed for CLI input. Whether the threat model shift from "local user" to "LLM client" requires strengthening those defenses was not audited because pipeline modules were out of diff scope. This is the most important open question for the next cycle.
