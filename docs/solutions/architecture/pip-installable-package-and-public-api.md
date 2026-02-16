---
title: "Pip-Installable Package: Public API Boundary and Validation Ownership"
date: 2026-02-15
category: architecture
tags:
  - packaging
  - pyproject-toml
  - public-api
  - validation-ownership
  - dataclass
  - cli-extraction
  - additive-pattern
module: __init__.py, results.py, cli.py, agent.py, modes.py, pyproject.toml
symptoms: |
  Project only runnable via `python main.py` from repo root. No programmatic API.
  No structured return type — callers get raw markdown string. Can't install as
  a package or run from other directories.
severity: low
summary: |
  Converting a script-based project to a pip-installable package exposes API boundary
  decisions (what to export, what to validate, where validation lives). Key lesson:
  validation logic belongs in the module that owns the data, not duplicated in callers.
  The additive pattern (wrap, don't refactor) keeps the migration safe.
---

# Pip-Installable Package: Public API Boundary and Validation Ownership

## Problem

The research agent worked only as `python main.py "query"` from the repo root. Three gaps:

1. **No package install** — couldn't `pip install` or run from other directories
2. **No public API** — programmatic callers had to instantiate `ResearchAgent` directly and handle mode objects, async lifecycle, and env vars themselves
3. **No structured return** — `agent.research()` returns a bare `str`, discarding metadata (source count, gate decision) that programmatic callers need

## Solution

Four-session additive approach — no existing module signatures changed:

### 1. Structured return types (`results.py`)

```python
@dataclass(frozen=True)
class ResearchResult:
    report: str
    query: str
    mode: str
    sources_used: int  # sources surviving relevance gate
    status: str        # gate decision: full_report/short_report/insufficient_data

@dataclass(frozen=True)
class ModeInfo:
    name: str
    max_sources: int
    word_target: int
    cost_estimate: str
    auto_save: bool
```

Follows the codebase's established frozen dataclass pattern (13 existing).

### 2. Source tracking via private attrs (`agent.py`)

Added `_last_source_count` and `_last_gate_decision` to `ResearchAgent.__init__`, set during `_evaluate_and_synthesize()`, read by `run_research()` after calling `.research_async()`. This avoids changing the internal method signature — the attrs are an internal contract between two files in the same package.

### 3. Public API (`__init__.py`)

```python
def run_research(query: str, mode: str = "standard") -> ResearchResult: ...
async def run_research_async(query: str, mode: str = "standard") -> ResearchResult: ...
def list_modes() -> list[ModeInfo]: ...
```

Key design decisions:
- **Sync wrapper with async escape hatch** — `run_research()` calls `asyncio.run()`, catches the event-loop-already-running error and points callers to `run_research_async()`
- **Env var validation up front** — checks `ANTHROPIC_API_KEY` and `TAVILY_API_KEY` before creating the agent, failing fast instead of 30s into the pipeline
- **Mode validation delegated to `ResearchMode.from_name()`** — see Root Cause below

### 4. CLI extraction (`cli.py`) and packaging (`pyproject.toml`)

Moved all CLI logic from `main.py` to `research_agent/cli.py`. `main.py` becomes a 2-line shim for backward compatibility. `pyproject.toml` with `[project.scripts]` wires `research-agent` as a console command.

## Root Cause: Validation Ownership Duplication

The most instructive bug in this cycle: the original plan specified a `_VALID_MODES` frozenset in `__init__.py` to validate mode names:

```python
# Bad: duplicated knowledge
_VALID_MODES = frozenset({"quick", "standard", "deep"})  # __init__.py
# Also defined in modes.py via from_name() classmethod
```

This meant adding a new mode to `modes.py` would silently fail validation in `__init__.py`. The review caught it as P1. The fix: delegate validation to `ResearchMode.from_name()` and catch the `ValueError`:

```python
# Good: single source of truth
try:
    research_mode = ResearchMode.from_name(mode)
except ValueError:
    raise ResearchError(f"Invalid mode: {mode!r}. ...")
```

**Pattern:** When module A validates data that module B owns, A is duplicating B's knowledge. Delegate to B and translate the exception to your public error type.

## Additional Learnings

### Private attrs are acceptable internal contracts

The Python reviewer raised concerns about `run_research()` reading `agent._last_source_count` (a private attr). The alternative — changing `research_async()` to return a `_ResearchOutcome` — would modify internal method signatures, breaking the additive constraint. The private attr approach is acceptable when:
- The caller is in the same package (not a third-party consumer)
- The contract is documented and tested
- The alternative adds more complexity than it removes

### `list_modes()` should return typed objects, not dicts

Early versions returned `list[dict]`. Pattern recognition found every other public function in the codebase returns typed objects. Raw dicts lose IDE autocomplete, type checking, and frozen immutability. The `ModeInfo` dataclass costs 8 lines and preserves the established pattern.

### Library functions should not call `load_dotenv()`

`run_research()` intentionally does NOT call `load_dotenv()`. Library functions should not have global side effects. The CLI entry point owns env setup. Document this for library callers.

### Editable install gotcha with entry points

After adding `[project.scripts]` to `pyproject.toml`, you must re-run `pip install -e .` to register the console command. Entry points don't auto-update in editable mode. This is a setuptools limitation.

### `open -t` prevents file execution

The security review found `subprocess.run(["open", str(path)])` could execute a file disguised as `.md`. Using `open -t` forces macOS to use a text editor regardless of file permissions. Simple fix for a real risk.

## Prevention

1. **Validation ownership rule:** If you're hardcoding a set of valid values, check if another module already defines them. If so, delegate.
2. **Public API checklist:** For every public function, ask: what does the caller need to set up before calling? (env vars, working directory, event loop). Validate or document each prerequisite.
3. **Return typed objects:** Never return raw dicts from public APIs. A frozen dataclass costs 5-10 lines and provides immutability, IDE support, and type safety.
4. **Additive migrations:** When converting scripts to packages, wrap existing internals with thin public functions. Don't refactor internals in the same cycle.

## Related

- `research_agent/__init__.py` — public API functions
- `research_agent/results.py` — ResearchResult, ModeInfo
- `research_agent/modes.py` — ResearchMode.from_name() (validation owner)
- `research_agent/cli.py` — extracted CLI
- `docs/solutions/architecture/agent-native-return-structured-data.md` — prior learning on structured returns
- Cycle 19 (planned) — MCP server, first consumer of the public API
