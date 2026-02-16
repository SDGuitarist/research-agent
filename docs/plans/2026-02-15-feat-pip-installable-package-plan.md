---
title: "feat: Pip-Installable Package"
type: feat
date: 2026-02-15
cycle: 18
brainstorm: docs/brainstorms/2026-02-15-cycle-18-pip-installable-package.md
---

# feat: Pip-Installable Package

## Overview

Convert the research agent from a folder of scripts (`python main.py "query"`) into a proper pip-installable Python package that can be:

1. **Installed locally** with `pip install -e .`
2. **Run from any directory** as `research-agent "query"`
3. **Imported programmatically** via `from research_agent import run_research`

This is the critical enabler for Cycle 19 (MCP server) and Cycle 20 (REST API). It forces a clean public API boundary.

## Problem Statement / Motivation

The codebase is already structured as a Python package (`research_agent/` with `__init__.py`), but it isn't installable. Users must `cd` into the project directory and run `python main.py`. There's no public API for programmatic callers, and no structured return type — just a raw markdown string.

## Proposed Solution

Additive approach — no internal refactoring required:

1. Create `ResearchResult` frozen dataclass as structured return type
2. Add `run_research()` + `run_research_async()` + `list_modes()` public API functions
3. Extract CLI from `main.py` to `research_agent/cli.py`
4. Create `pyproject.toml` with dependencies and console_scripts entry point
5. Verify `pip install -e .` end-to-end

## Technical Considerations

### Source count tracking

`agent.research()` returns a raw `str`. To populate `ResearchResult.sources_used`, we need the count of sources that survived the relevance gate. The least invasive approach: add `self._last_source_count: int` and `self._last_gate_decision: str` instance attributes to `ResearchAgent`, set them in `_evaluate_and_synthesize()` (line 391: `len(evaluation.surviving_sources)` is already computed), read them from `run_research()` after calling `.research()`.

**Definition:** `sources_used` = number of sources surviving the relevance gate (the sources that actually contributed to the report).

### Event loop safety

`run_research()` wraps `asyncio.run()`, which fails if an event loop is already running (Jupyter, MCP, FastAPI). Solution: also export `run_research_async()` so async callers have a first-class path. This directly enables Cycle 19.

### load_dotenv behavior

`run_research()` will NOT call `load_dotenv()`. Library functions should not have global side effects. The CLI entry point continues to call `load_dotenv()`. Early env var validation added instead — check for `ANTHROPIC_API_KEY` before creating the agent.

### Dependency: httpcore

`fetch.py` imports `httpcore` directly (line 12) but it's only declared transitively via `httpx`. Add `httpcore>=1.0.0` to `pyproject.toml` dependencies.

### Python version

`requires-python = ">=3.10"` — the codebase uses `X | Y` union syntax (3.10+). Only Python 3.14 is tested, but 3.10 is the actual floor. Document this.

## Acceptance Criteria

- [ ] `pip install -e .` succeeds from repo root
- [ ] `research-agent --help` works from any directory (after install)
- [ ] `research-agent "test query" --quick` produces a report
- [ ] `python main.py "test query" --quick` still works (backward compat)
- [ ] `from research_agent import run_research, ResearchResult` works
- [ ] `result = run_research("query", mode="quick")` returns a `ResearchResult`
- [ ] `result.report`, `.mode`, `.query`, `.sources_used`, `.status` all populated
- [ ] `list_modes()` returns useful mode info
- [ ] `run_research(mode="invalid")` raises `ResearchError`, not `ValueError`
- [ ] `run_research("")` raises `ResearchError` for empty query
- [ ] All 527 existing tests pass
- [ ] New tests for `ResearchResult`, `run_research`, `list_modes`, `cli.py`

## Dependencies & Risks

- **Low risk:** The approach is additive — no existing module signatures change
- **Test imports safe:** All tests import from submodules (`from research_agent.agent import ...`), not package root
- **Stdout noise:** agent.py prints ~30 progress lines during research. Known tech debt, deferred to pre-Cycle 19 logging conversion. Documented in `run_research()` docstring.
- **CWD-relative paths:** `REPORTS_DIR`, `RESEARCH_LOG_PATH`, `research_context.md` resolve from CWD. Fine for CLI, documented for library callers.

---

## Implementation Sessions

### Session 1: ResearchResult dataclass + source count tracking

**New file:** `research_agent/results.py`
**Modified:** `research_agent/agent.py`
**Tests:** `tests/test_results.py`
**~60 lines**

#### 1a. Create `research_agent/results.py`

```python
# research_agent/results.py
"""Structured result type for the research agent public API."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchResult:
    """Result from a research query.

    Attributes:
        report: The markdown report.
        query: The original query string.
        mode: The research mode name (quick/standard/deep).
        sources_used: Number of sources that contributed to the report.
        status: Gate decision — "full_report", "short_report",
                "insufficient_data", or "no_new_findings".
    """
    report: str
    query: str
    mode: str
    sources_used: int
    status: str
```

#### 1b. Add source tracking to `ResearchAgent` in `agent.py`

Add two instance attributes in `__init__` (after line 60):

```python
self._last_source_count: int = 0
self._last_gate_decision: str = ""
```

Set them in `_evaluate_and_synthesize()` (around line 391):

```python
self._last_source_count = len(evaluation.surviving_sources)
self._last_gate_decision = evaluation.decision
```

Also set for the insufficient_data/no_new_findings branch (around line 376):

```python
self._last_source_count = 0
self._last_gate_decision = evaluation.decision
```

#### 1c. Tests for `ResearchResult` in `tests/test_results.py`

- Frozen immutability (cannot assign to fields)
- All fields accessible
- Repr works (useful for debugging)

---

### Session 2: Public API functions

**Modified:** `research_agent/__init__.py`
**Tests:** `tests/test_public_api.py`
**~90 lines**

#### 2a. Update `research_agent/__init__.py`

```python
# research_agent/__init__.py
"""Research agent — search the web and generate structured reports."""

__version__ = "0.18.0"

import asyncio
import os

from .agent import ResearchAgent
from .errors import ResearchError
from .modes import ResearchMode
from .results import ResearchResult

__all__ = [
    "ResearchAgent",
    "ResearchMode",
    "ResearchResult",
    "ResearchError",
    "run_research",
    "run_research_async",
    "list_modes",
]


def run_research(query: str, mode: str = "standard") -> ResearchResult:
    """Run a research query and return a structured result.

    Args:
        query: The research question.
        mode: Research mode — "quick", "standard", or "deep".

    Returns:
        ResearchResult with report, query, mode, sources_used, status.

    Raises:
        ResearchError: If query is empty, mode is invalid,
            API keys are missing, or research fails.

    Note:
        The research agent prints progress to stdout during execution.
        Set ANTHROPIC_API_KEY and TAVILY_API_KEY environment variables
        before calling.
    """
    return asyncio.run(run_research_async(query, mode=mode))


async def run_research_async(query: str, mode: str = "standard") -> ResearchResult:
    """Async version of run_research for use in async contexts.

    Same interface as run_research(). Use this when calling from
    an async context (MCP servers, FastAPI, Jupyter, etc.)
    where asyncio.run() would fail.
    """
    if not query or not query.strip():
        raise ResearchError("Query cannot be empty")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise ResearchError(
            "ANTHROPIC_API_KEY environment variable is required"
        )

    try:
        research_mode = ResearchMode.from_name(mode)
    except ValueError as e:
        raise ResearchError(str(e)) from e

    agent = ResearchAgent(mode=research_mode)
    report = await agent.research_async(query)

    return ResearchResult(
        report=report,
        query=query,
        mode=research_mode.name,
        sources_used=agent._last_source_count,
        status=agent._last_gate_decision,
    )


def list_modes() -> list[dict]:
    """List available research modes with their configuration.

    Returns:
        List of dicts with keys: name, max_sources, word_target,
        cost_estimate, auto_save.
    """
    modes = [ResearchMode.quick(), ResearchMode.standard(), ResearchMode.deep()]
    return [
        {
            "name": m.name,
            "max_sources": m.max_sources,
            "word_target": m.word_target,
            "cost_estimate": m.cost_estimate,
            "auto_save": m.auto_save,
        }
        for m in modes
    ]
```

#### 2b. Tests for public API in `tests/test_public_api.py`

- `run_research()` with valid mode (mock `ResearchAgent.research_async`)
- `run_research()` with invalid mode raises `ResearchError`
- `run_research("")` raises `ResearchError`
- `run_research()` without `ANTHROPIC_API_KEY` raises `ResearchError`
- `run_research_async()` same validation tests
- `list_modes()` returns 3 dicts with expected keys
- `list_modes()` names are quick, standard, deep
- `__version__` is "0.18.0"
- `__all__` contains all expected names

---

### Session 3: CLI extraction

**New file:** `research_agent/cli.py`
**Modified:** `main.py`
**Modified:** `tests/test_main.py` (update imports)
**~30 lines new** (mostly moved code)

#### 3a. Create `research_agent/cli.py`

Move all 6 functions from `main.py` into `cli.py`:
- `sanitize_filename()`
- `append_research_log()`
- `get_auto_save_path()`
- `list_reports()`
- `show_costs()`
- `main()`

Keep all imports. Keep `RESEARCH_LOG_PATH` and `REPORTS_DIR` constants. The `main()` function stays identical — it imports from `research_agent` and `research_agent.errors` which continue to work.

Update the `main()` docstring examples to use `research-agent` command alongside `python main.py`.

#### 3b. Simplify `main.py` to shim

```python
#!/usr/bin/env python3
"""CLI entry point — delegates to research_agent.cli.main()."""
from research_agent.cli import main

if __name__ == "__main__":
    main()
```

#### 3c. Update `tests/test_main.py`

Update import paths. Tests that import from `main` or mock functions in `main` need to point to `research_agent.cli` instead. The test logic stays identical — only the module path changes.

Verify: `python -m pytest tests/test_main.py -v` passes.

---

### Session 4: pyproject.toml + integration verification

**New file:** `pyproject.toml`
**Modified:** `pytest.ini` (delete — migrated to pyproject.toml)
**~50 lines**

#### 4a. Create `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "research-agent"
version = "0.18.0"
description = "CLI research agent that searches the web and generates structured markdown reports"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}

dependencies = [
    "anthropic>=0.40.0",
    "httpx>=0.27.0",
    "httpcore>=1.0.0",
    "ddgs>=9.0.0",
    "tavily-python>=0.3.0",
    "trafilatura>=1.12.0",
    "readability-lxml>=0.8.0",
    "python-dotenv>=1.0.0",
    "PyYAML>=6.0",
]

[project.optional-dependencies]
test = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[project.scripts]
research-agent = "research_agent.cli:main"

[tool.setuptools.packages.find]
include = ["research_agent*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

#### 4b. Delete `pytest.ini`

Config migrated to `[tool.pytest.ini_options]` in `pyproject.toml`.

#### 4c. Integration verification checklist

Run these commands to verify everything works:

```bash
# 1. Install in editable mode
pip install -e .

# 2. CLI works from any directory
cd /tmp && research-agent --help
cd /tmp && research-agent --cost
cd /tmp && research-agent --list

# 3. Import works
python -c "from research_agent import run_research, list_modes, ResearchResult; print(list_modes())"
python -c "from research_agent import __version__; print(__version__)"

# 4. Backward compat
cd /path/to/research-agent && python main.py --help

# 5. All tests pass
cd /path/to/research-agent && python -m pytest tests/ -v
```

#### 4d. Keep `requirements.txt`

Add a comment noting `pyproject.toml` is the canonical source:

```
# Canonical dependency list is in pyproject.toml.
# This file is kept for quick `pip install -r requirements.txt` workflows.
```

---

## File Change Summary

| File | Action | Session |
|------|--------|---------|
| `research_agent/results.py` | Create | 1 |
| `research_agent/agent.py` | Add 4 lines (source tracking) | 1 |
| `tests/test_results.py` | Create | 1 |
| `research_agent/__init__.py` | Rewrite (public API) | 2 |
| `tests/test_public_api.py` | Create | 2 |
| `research_agent/cli.py` | Create (move from main.py) | 3 |
| `main.py` | Simplify to 2-line shim | 3 |
| `tests/test_main.py` | Update import paths | 3 |
| `pyproject.toml` | Create | 4 |
| `pytest.ini` | Delete (migrated) | 4 |
| `requirements.txt` | Add comment | 4 |

## Known Limitations (Carry Forward to Cycle 19)

- **Stdout noise:** `agent.py` prints ~30 progress lines. Must convert to `logging` module before MCP server.
- **CWD-relative paths:** `REPORTS_DIR`, `RESEARCH_LOG_PATH`, `research_context.md` resolve from CWD.
- **No TAVILY_API_KEY validation:** Only `ANTHROPIC_API_KEY` is checked upfront. Tavily key failure surfaces later in the pipeline as a `SearchError`.
- **Version sync:** `__version__` in `__init__.py` and `version` in `pyproject.toml` must be bumped together.

## References & Research

- Brainstorm: `docs/brainstorms/2026-02-15-cycle-18-pip-installable-package.md`
- Existing `__init__.py`: `research_agent/__init__.py`
- CLI entry point: `main.py:133` (`main()` function)
- Source count: `research_agent/agent.py:391` (`len(evaluation.surviving_sources)`)
- Gate decision: `research_agent/agent.py:376` (`evaluation.decision`)
- Mode config: `research_agent/modes.py` (frozen dataclass with `from_name()` classmethod)
- Error hierarchy: `research_agent/errors.py` (ResearchError base, 5 subclasses)
- Institutional learning: `docs/solutions/architecture/agent-native-return-structured-data.md`
