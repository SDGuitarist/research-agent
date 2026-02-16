# Cycle 18: Pip-Installable Package — Brainstorm

**Date:** 2026-02-15
**Cycle:** 18
**Status:** Brainstorm complete — ready for planning

---

## What We're Building

Turn the research agent from "a folder of scripts you run with `python main.py`" into a proper Python package that can be:

1. **Installed locally** with `pip install -e .`
2. **Run from any directory** as `research-agent "query"`
3. **Imported programmatically** via `from research_agent import run_research`

This is the critical enabler for Cycle 19 (MCP server) and Cycle 20 (REST API). It forces a clean public API boundary.

---

## Why This Approach

The codebase is already structured as a Python package (`research_agent/` with `__init__.py`). What's missing is:

- A `pyproject.toml` to make it installable
- A CLI entry point so `research-agent` works as a command
- A clean public API beyond the raw `ResearchAgent` class
- A structured return type for programmatic callers

The approach is additive — no internal refactoring required. We wrap existing internals with thin public functions and add packaging metadata.

---

## Key Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | API surface | `run_research` + `list_modes` (2 functions) | Covers the primary use case. Gaps API deferred — too coupled to internal types. |
| 2 | Return type | `ResearchResult` frozen dataclass | `.report`, `.mode`, `.query`, `.sources_used`. Useful for MCP/REST later. |
| 3 | Stdout noise | Ignore for now | Agent prints progress to stdout. Callers can redirect. Convert to `logging` module before Cycle 19. |
| 4 | Public/internal boundary | `__all__` in `__init__.py` | Exports only: `run_research`, `list_modes`, `ResearchResult`, `ResearchAgent`, `ResearchMode`. |
| 5 | CLI command name | `research-agent` | Matches repo name. Hyphens standard for CLI tools. |
| 6 | Install target | Local first (`pip install -e .`) | PyPI deferred. Structure supports both. |
| 7 | CLI approach | Extract to `cli.py`, wire as entry point | Zero rework on existing CLI logic. `main.py` becomes a thin shim. |
| 8 | Version | `0.18.0` | Ties to Cycle 18. Hardcoded in `__init__.py`. Dynamic versioning deferred to PyPI publish. |

---

## Codebase Findings

### What already works

- `__init__.py` already exports `ResearchAgent` and `ResearchMode`
- `agent.research()` returns a clean `str` (markdown report)
- `agent.research_async()` exists for async callers
- `ResearchMode.from_name()` exists — useful for `run_research(query, mode="deep")`
- `main.py` has a clean `main()` function, easy to wire as entry point
- Tests import from submodules (`from research_agent.agent import ...`) — paths won't change
- `requirements.txt` has all 8 runtime deps + 2 test deps

### What needs work

- **No `pyproject.toml` or `setup.py`** — package isn't installable
- **`agent.py` prints to stdout** — ~20 progress lines during research. Not blocking for Cycle 18 but must fix before Cycle 19
- **CLI logic lives in `main.py`** — needs extraction to `research_agent/cli.py` for proper entry point
- **No structured return type** — `research()` returns raw string, need `ResearchResult` wrapper
- **Hardcoded paths in `main.py`** — `RESEARCH_LOG_PATH` and `REPORTS_DIR` are relative to CWD, which is fine for CLI but should be documented

### No risks found

- **Circular imports:** Not a concern. `__init__.py` → `agent.py` is a simple chain.
- **Test breakage:** Tests import from submodules, not package root. All paths survive.
- **Dependency completeness:** `requirements.txt` covers everything. Will transfer to `pyproject.toml`.

---

## Deliverable Sequence (Preliminary)

The plan phase should finalize ordering, but this sequence respects dependencies:

1. **`ResearchResult` dataclass** (`research_agent/results.py`) — no dependencies, enables everything else
2. **Public API functions** (`research_agent/__init__.py`) — depends on #1, thin wrappers
3. **CLI extraction** (`research_agent/cli.py`) — depends on #2, routes through public API
4. **Package config** (`pyproject.toml`) — depends on #3 for entry point definition
5. **Integration verification** — depends on all above, test `pip install -e .` end-to-end

---

## Known Limitations (Carry Forward)

- **Stdout prints from agent.py** — Public API functions inherit progress prints. Must convert to `logging` module before Cycle 19 (MCP server). Track this as a known tech debt item.
- **Relative paths** — `REPORTS_DIR` and `RESEARCH_LOG_PATH` in CLI are CWD-relative. Fine for CLI, but programmatic callers should be aware.
- **No async public API** — `run_research` will be sync (wraps `asyncio.run`). Async callers can use `ResearchAgent.research_async()` directly. Consider adding `run_research_async` if MCP needs it.

---

## Out of Scope

- Publishing to PyPI
- MCP server (Cycle 19)
- REST API (Cycle 20)
- New research features
- CI/CD
- Converting prints to logging (pre-Cycle 19 task)
- Gap checking public API (types too unstable)

---

## Resolved Questions

1. **`main.py` → keep as shim.** Two lines: `from research_agent.cli import main; main()`. Preserves backward compat for `python main.py` users and existing CLAUDE.md docs. Zero cost.
2. **`__version__` → hardcoded in `__init__.py`.** `__version__ = "0.18.0"`. Dynamic versioning (importlib.metadata) is complexity for a problem we don't have. Switch to dynamic when publishing to PyPI.
3. **`run_research` → no `api_key` parameter.** Agent reads keys from env vars. Adding a parameter creates hardcoding risk. Env vars work for local, MCP, and REST alike. Existing errors already tell callers if keys are missing.

**Version bump:** `0.18.0` (not `0.17.0`) — ties to Cycle 18.
