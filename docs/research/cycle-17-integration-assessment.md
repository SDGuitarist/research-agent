# Cycle 17 Integration Assessment

**Date:** 2026-02-15
**Inputs:** `docs/research/research-agent-integrations.md`, Cycle 17 brainstorm (17-01 through 17-05)
**Question:** Can any integrations be done during Cycle 17, or should they wait?

---

## Verdict: Do 17A-17D First, Then Integrate

The Cycle 17 plan (17A-17D) is internally focused — error hierarchy, gap schema, state persistence, pipeline integration. It's ~910 lines across 4 sub-cycles, each building on the previous one. That's already a full cycle of work.

---

## Integration Fit Analysis

| Integration | Fits in 17? | Why / Why Not |
|---|---|---|
| **MCP Server** | No | Needs stable public API surface. 17D changes `context.py`, `relevance.py`, `agent.py` — the exact modules you'd wrap. Building MCP on a moving target means double work. |
| **REST API (FastAPI)** | No | Same reason plus external deps (FastAPI, uvicorn, auth). The deferred items list in 17-05 already excludes external-dependency features for this reason. |
| **Workflow Hooks (Zapier/n8n)** | No | Depends on having either the MCP server or REST API first. This is 2+ cycles away. |
| **CLI stays valuable** | Already done | Already aligned with the market. |
| **Embedded Library (pip)** | Maybe after 17D | Closest candidate — mostly packaging (`pyproject.toml`, clean `__init__.py` exports). But 17D changes the public-facing methods in `agent.py`, so packaging before that means re-exporting. |

---

## Key Dependency: Foundation Before Features

The Cycle 17 brainstorm explicitly states:

> "Foundation before features." Infrastructure gaps must exist before any feature code touches agent.py.

Integrations are features that expose the pipeline externally. They depend on:

- **Clean error types (17A)** — so API/MCP can return structured errors, not raw exceptions
- **Token budgeting (17A)** — critical for API usage where you need cost control per request
- **State persistence (17C)** — useful for an API that tracks research across calls
- **`ContextResult` type (17A)** — so MCP tools return structured status, not `None`

---

## Recommended Sequence

```
17A -> 17B -> 17C -> 17D  (current plan, ~4 sessions)
         |
Cycle 18: Embedded Library (pip-installable package)
         |
Cycle 19: MCP Server (expose search/fetch/synthesize as tools)
         |
Cycle 20+: REST API -> Workflow Hooks
```

### Cycle 18: Embedded Library

The natural first integration because:

- Mostly packaging, not new code
- GPT-Researcher's pip install is their #2 interface after CLI
- Forces definition of a clean public API, which MCP and REST will reuse
- Low external dependency risk

### Cycle 19: MCP Server

Second because:

- MCP is the dominant protocol for LLM tool access (adopted by OpenAI, Google, Microsoft)
- GPT-Researcher's MCP (`gptr-mcp`) is a good reference implementation
- Pipeline stages (search, fetch, synthesize) map cleanly to MCP tools
- Gives integration with Claude Code, Cursor, and other LLM clients for free

### Cycle 20+: REST API and Workflow Hooks

Later because:

- REST API needs web server infrastructure, authentication, rate limiting
- Workflow hooks depend on having the REST API or MCP server first
- Higher external dependency risk

---

## Optional Prep (No Code Required)

Document the public API surface in a short spec (which methods, which params, which return types). Takes 30 minutes, costs no code, and makes Cycle 18 packaging trivial. The 17-01 codebase analysis already maps extension points well.
