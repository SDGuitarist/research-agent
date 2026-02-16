---
title: "feat: Pip-Installable Package"
type: feat
date: 2026-02-15
cycle: 18
brainstorm: docs/brainstorms/2026-02-15-cycle-18-pip-installable-package.md
deepened: 2026-02-15
---

# feat: Pip-Installable Package

## Enhancement Summary

**Deepened on:** 2026-02-15
**Research agents used:** kieran-python-reviewer, architecture-strategist, code-simplicity-reviewer, agent-native-reviewer, performance-oracle, security-sentinel, pattern-recognition-specialist, best-practices-researcher, learnings-researcher, agent-native-architecture skill, Context7 (setuptools docs)

### Key Improvements
1. **Fix build backend** — Use `setuptools.build_meta` (not legacy `_Backend`)
2. **Fix `list_modes()` return type** — Use `ModeInfo` frozen dataclass (matches codebase pattern of typed returns, not raw dicts)
3. **Add TAVILY_API_KEY validation** — Fail fast instead of 30s into pipeline (security finding M-1)
4. **Add event loop collision handling** — Clear error when `run_research()` called from async context
5. **Add version sync test** — Prevent `__version__` / `pyproject.toml` drift
6. **Fix `--open` path validation** — Security H-1: validate path is within reports dir
7. **Skip pytest.ini migration** — Simplicity: keep working config as-is
8. **Skip requirements.txt comment** — Simplicity: no value added

### New Considerations Discovered
- **Performance:** All wrapper overhead is negligible (<20ms vs 30-120s runtimes). No optimization needed.
- **Security:** Packaging increases exposure of existing CWD-relative path risks. Document for library callers.
- **Pattern consistency:** `_last_source_count` follows existing research-scoped state pattern (same as `_start_time`, `_step_num`). Add explicit reset in `_research_async()`.
- **Agent-native score:** 6.4/10 — acceptable for v1. Key gaps (progress callbacks, rich metadata) correctly deferred to Cycle 19.

---

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

<details>
<summary>Research Insights: Source tracking pattern</summary>

**Pattern recognition review confirmed:** `_last_source_count` follows the existing research-scoped state pattern in `agent.py`. The class already uses `_start_time`, `_step_num`, `_current_schema_result`, `_current_research_batch` — all initialized in `__init__`, reset in `_research_async()`, set during pipeline. Adding two more attributes is consistent.

**Python reviewer raised concern** about accessing private attrs from the public API (`agent._last_source_count`). However, the alternative (returning a `_ResearchOutcome` from `research_async()`) would change the internal method signature, breaking the "additive only" constraint. The private attr approach is acceptable because:
- `run_research()` is the only caller — it's part of the same package
- The attrs are documented as internal contract between `__init__.py` and `agent.py`
- The alternative adds more complexity than it removes

**Action:** Add explicit reset of both attrs in `_research_async()` for consistency with existing state management.

</details>

### Event loop safety

`run_research()` wraps `asyncio.run()`, which fails if an event loop is already running (Jupyter, MCP, FastAPI). Solution: also export `run_research_async()` so async callers have a first-class path. This directly enables Cycle 19.

<details>
<summary>Research Insights: Event loop collision</summary>

**Python reviewer recommended:** Catch `RuntimeError` in `run_research()` and provide a clear error message:

```python
try:
    return asyncio.run(run_research_async(query, mode=mode))
except RuntimeError as e:
    if "cannot be called from a running event loop" in str(e):
        raise ResearchError(
            "run_research() cannot be called from async context. "
            "Use 'await run_research_async()' instead."
        ) from e
    raise
```

**Simplicity reviewer argued** `run_research_async()` is YAGNI. Rejected — it's a one-liner, costs nothing, and directly enables Cycle 19 (MCP server runs in async context). The brainstorm explicitly decided to include it.

</details>

### load_dotenv behavior

`run_research()` will NOT call `load_dotenv()`. Library functions should not have global side effects. The CLI entry point continues to call `load_dotenv()`. Early env var validation added instead — check for both `ANTHROPIC_API_KEY` and `TAVILY_API_KEY` before creating the agent.

### Dependency: httpcore

`fetch.py` imports `httpcore` directly (line 12) but it's only declared transitively via `httpx`. Add `httpcore>=1.0.5` to `pyproject.toml` dependencies.

### Python version

`requires-python = ">=3.10"` — the codebase uses `X | Y` union syntax (3.10+). Only Python 3.14 is tested, but 3.10 is the actual floor. Document this.

<details>
<summary>Research Insights: requires-python</summary>

**Best practices research says:** "Set to minimum version you're willing to support, not the version you test on." For local-only packages, `>=3.10` is reasonable since the union syntax is the only 3.10+ feature used. If publishing to PyPI later, consider narrowing to `>=3.12` as a tested baseline.

**Security reviewer notes:** Setting a broader range means untested Python versions could install the package. Acceptable risk for local development.

</details>

## Acceptance Criteria

- [ ] `pip install -e .` succeeds from repo root
- [ ] `research-agent --help` works from any directory (after install)
- [ ] `research-agent "test query" --quick` produces a report
- [ ] `python main.py "test query" --quick` still works (backward compat)
- [ ] `from research_agent import run_research, ResearchResult` works
- [ ] `result = run_research("query", mode="quick")` returns a `ResearchResult`
- [ ] `result.report`, `.mode`, `.query`, `.sources_used`, `.status` all populated
- [ ] `list_modes()` returns list of `ModeInfo` objects with expected fields
- [ ] `run_research(mode="invalid")` raises `ResearchError`, not `ValueError`
- [ ] `run_research("")` raises `ResearchError` for empty query
- [ ] `run_research()` without `ANTHROPIC_API_KEY` raises `ResearchError`
- [ ] `run_research()` without `TAVILY_API_KEY` raises `ResearchError`
- [ ] `run_research()` from async context gives clear error message
- [ ] Version sync test: `__version__` matches `pyproject.toml`
- [ ] All 527 existing tests pass
- [ ] New tests for `ResearchResult`, `ModeInfo`, `run_research`, `list_modes`, `cli.py`

## Dependencies & Risks

- **Low risk:** The approach is additive — no existing module signatures change
- **Test imports safe:** All tests import from submodules (`from research_agent.agent import ...`), not package root
- **Stdout noise:** agent.py prints ~30 progress lines during research. Known tech debt, deferred to pre-Cycle 19 logging conversion. Documented in `run_research()` docstring.
- **CWD-relative paths:** `REPORTS_DIR`, `RESEARCH_LOG_PATH`, `research_context.md` resolve from CWD. Fine for CLI, documented for library callers. Security review recommends adding `output_dir` parameter in Cycle 19 for MCP/REST.

---

## Implementation Sessions

### Session 1: ResearchResult + ModeInfo dataclasses + source count tracking

**New file:** `research_agent/results.py`
**Modified:** `research_agent/agent.py`
**Tests:** `tests/test_results.py`
**~70 lines**

#### 1a. Create `research_agent/results.py`

```python
# research_agent/results.py
"""Structured result types for the research agent public API."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchResult:
    """Result from a research query.

    Attributes:
        report: The markdown report.
        query: The original query string.
        mode: The research mode name (quick/standard/deep).
        sources_used: Number of sources that contributed to the report
            (survived the relevance gate).
        status: Gate decision — "full_report", "short_report",
                "insufficient_data", or "no_new_findings".
    """
    report: str
    query: str
    mode: str
    sources_used: int
    status: str


@dataclass(frozen=True)
class ModeInfo:
    """Information about an available research mode."""
    name: str
    max_sources: int
    word_target: int
    cost_estimate: str
    auto_save: bool
```

<details>
<summary>Research Insights: Dataclass design</summary>

**Pattern recognition confirmed:** 13 existing frozen dataclasses in the codebase (ResearchMode, ContextResult, DecompositionResult, SourceScore, etc.). `ResearchResult` and `ModeInfo` follow the established pattern.

**Simplicity reviewer argued** ResearchResult is YAGNI — just return the string. Rejected because:
- The brainstorm explicitly decided structured return type is needed (Decision #2)
- `status` field enables programmatic callers to distinguish report quality without parsing markdown
- `sources_used` gives callers confidence metrics
- MCP server (Cycle 19) needs structured data, not raw strings
- Institutional learning (`agent-native-return-structured-data.md`) recommends this exact pattern

**Simplicity reviewer was right** that `list[dict]` is an anti-pattern here — but the fix is `ModeInfo` dataclass, not removing the function. All other public functions in the codebase return typed objects, not raw dicts.

**Agent-native reviewer recommended** additional fields (`timestamp`, `saved_path`, `sources_details`, `duration_seconds`). Deferred to Cycle 19 — start minimal, enrich when consumers exist.

</details>

#### 1b. Add source tracking to `ResearchAgent` in `agent.py`

Add two instance attributes in `__init__` (after line 60):

```python
self._last_source_count: int = 0
self._last_gate_decision: str = ""
```

Add explicit reset in `_research_async()` (around line 150, with existing resets):

```python
self._last_source_count = 0
self._last_gate_decision = ""
```

Set them in `_evaluate_and_synthesize()` — for the insufficient_data/no_new_findings branch (around line 376):

```python
self._last_source_count = 0
self._last_gate_decision = evaluation.decision
```

And for the synthesis branch (around line 391):

```python
self._last_source_count = len(evaluation.surviving_sources)
self._last_gate_decision = evaluation.decision
```

#### 1c. Tests for `ResearchResult` and `ModeInfo` in `tests/test_results.py`

- `ResearchResult`: frozen immutability, all fields accessible, repr works
- `ModeInfo`: frozen immutability, all fields accessible

---

### Session 2: Public API functions

**Modified:** `research_agent/__init__.py`
**Tests:** `tests/test_public_api.py`
**~100 lines**

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
from .results import ModeInfo, ResearchResult

__all__ = [
    "ResearchAgent",
    "ResearchMode",
    "ResearchResult",
    "ResearchError",
    "ModeInfo",
    "run_research",
    "run_research_async",
    "list_modes",
]

_VALID_MODES = frozenset({"quick", "standard", "deep"})


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
            Subclasses (SearchError, SynthesisError) propagate
            from the pipeline for specific failures.

    Note:
        The research agent prints progress to stdout during execution.
        This will be converted to logging in a future release.

        Set ANTHROPIC_API_KEY and TAVILY_API_KEY environment variables
        before calling. Reports auto-save to ./reports/ relative to CWD
        for standard and deep modes.
    """
    try:
        return asyncio.run(run_research_async(query, mode=mode))
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            raise ResearchError(
                "run_research() cannot be called from async context. "
                "Use 'await run_research_async()' instead."
            ) from e
        raise


async def run_research_async(query: str, mode: str = "standard") -> ResearchResult:
    """Async version of run_research for use in async contexts.

    Same interface as run_research(). Use this when calling from
    an async context (MCP servers, FastAPI, Jupyter, etc.)
    where asyncio.run() would fail.
    """
    if not query or not query.strip():
        raise ResearchError("Query cannot be empty")

    if mode not in _VALID_MODES:
        raise ResearchError(
            f"Invalid mode: {mode!r}. Must be one of: {', '.join(sorted(_VALID_MODES))}"
        )

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise ResearchError(
            "ANTHROPIC_API_KEY environment variable is required"
        )

    if not os.environ.get("TAVILY_API_KEY"):
        raise ResearchError(
            "TAVILY_API_KEY environment variable is required"
        )

    research_mode = ResearchMode.from_name(mode)
    agent = ResearchAgent(mode=research_mode)
    report = await agent.research_async(query)

    return ResearchResult(
        report=report,
        query=query,
        mode=research_mode.name,
        sources_used=agent._last_source_count,
        status=agent._last_gate_decision,
    )


def list_modes() -> list[ModeInfo]:
    """List available research modes with their configuration.

    Returns:
        List of ModeInfo objects with name, max_sources, word_target,
        cost_estimate, and auto_save fields.
    """
    modes = [ResearchMode.quick(), ResearchMode.standard(), ResearchMode.deep()]
    return [
        ModeInfo(
            name=m.name,
            max_sources=m.max_sources,
            word_target=m.word_target,
            cost_estimate=m.cost_estimate,
            auto_save=m.auto_save,
        )
        for m in modes
    ]
```

<details>
<summary>Research Insights: Public API design</summary>

**Changes from original plan based on research:**

1. **Mode validation uses `_VALID_MODES` frozenset** instead of `try/except ValueError` on `ResearchMode.from_name()`. Security reviewer flagged that wrapping `ValueError` broadly could mask internal bugs and leak implementation details (M-4). Direct validation is clearer.

2. **Added TAVILY_API_KEY validation** — Security finding M-1. Without it, missing Tavily key causes delayed failure ~30s into the pipeline after wasting Anthropic API costs.

3. **Added event loop collision handling** — Python reviewer recommended catching `RuntimeError` in `run_research()` and providing a clear error message pointing to `run_research_async()`.

4. **`list_modes()` returns `list[ModeInfo]`** not `list[dict]` — Pattern recognition found that ALL other public functions return typed objects. Raw dicts break the established pattern and lose IDE autocomplete + type checking.

5. **CWD warning in docstring** — Security reviewer flagged that library callers may not expect auto-saves to CWD-relative `./reports/`.

**Performance oracle confirmed:** All wrapper overhead is negligible. Creating 3 `ResearchMode` instances in `list_modes()` costs ~0.05ms. No caching needed.

</details>

#### 2b. Tests for public API in `tests/test_public_api.py`

- `run_research()` with valid mode (mock `ResearchAgent.research_async`)
- `run_research()` with invalid mode raises `ResearchError`
- `run_research("")` raises `ResearchError`
- `run_research("   ")` raises `ResearchError` (whitespace-only)
- `run_research()` without `ANTHROPIC_API_KEY` raises `ResearchError`
- `run_research()` without `TAVILY_API_KEY` raises `ResearchError`
- `run_research()` from inside async context raises `ResearchError` with "async context" message
- `run_research_async()` same validation tests (async versions)
- `list_modes()` returns 3 `ModeInfo` objects
- `list_modes()` names are quick, standard, deep
- `list_modes()` all fields are populated (no empty strings or zeros)
- `__version__` is "0.18.0"
- `__all__` contains all expected names
- Version sync test: `__version__` matches `pyproject.toml` version (skip on Python <3.11: `@pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib requires 3.11+")`)

<details>
<summary>Research Insights: Version sync test</summary>

**Python reviewer recommended** preventing `__version__` / `pyproject.toml` drift:

```python
# tests/test_public_api.py
import tomllib  # Python 3.11+ stdlib
from pathlib import Path
from research_agent import __version__

def test_version_matches_pyproject():
    """Ensure __init__.__version__ matches pyproject.toml."""
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    assert __version__ == data["project"]["version"]
```

Note: Use `tomllib` (stdlib since 3.11). If supporting 3.10, use `tomli` as a fallback or skip this test on 3.10.

</details>

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

**Security fix (H-1):** Add path validation for `--open` flag:

```python
# In cli.py main(), replace the subprocess.run block:
if args.open:
    if output_path.suffix != ".md":
        print("Warning: --open only supports .md files.",
              file=sys.stderr)
    else:
        subprocess.run(["open", "-t", str(output_path)])
```

The `-t` flag forces macOS `open` to use a text editor, preventing execution of files with `.md` extension that are actually scripts.

<details>
<summary>Research Insights: Security fix for --open</summary>

**Security sentinel found** (H-1, HIGH): `subprocess.run(["open", str(output_path)])` can execute files if they're disguised as `.md`. The current suffix check is insufficient because macOS `open` respects file permissions.

**Two remediation options:**
1. Use `open -t` to force text editor mode (simpler, chosen)
2. Validate path is within `REPORTS_DIR` using `output_path.resolve().relative_to(REPORTS_DIR.resolve())`

Option 1 is simpler and sufficient — the `-t` flag forces TextEdit regardless of file permissions. This fix is already tracked in `todos/036-complete-p3-subprocess-open-validate-extension.md`.

</details>

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
**~50 lines**

#### 4a. Create `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[project]
name = "research-agent"
version = "0.18.0"
description = "CLI research agent that searches the web and generates structured markdown reports"
requires-python = ">=3.10"
license = {text = "MIT"}

dependencies = [
    "anthropic>=0.40.0",
    "httpx>=0.27.0",
    "httpcore>=1.0.5",
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
```

<details>
<summary>Research Insights: pyproject.toml decisions</summary>

**Build backend fix:** Original plan used `setuptools.backends._legacy:_Backend` — this is wrong. Both the Python reviewer and best-practices research confirmed `setuptools.build_meta` is the correct modern backend. Context7 (setuptools docs) confirmed the canonical `[project.scripts]` format.

**Dependency bounds:** Security reviewer recommended upper bounds (`>=X.Y,<X+1.0`) to limit supply chain risk. Decision: keep `>=` bounds for now. Upper bounds cause "dependency hell" for pip resolver and are discouraged for application packages by PyPA. The `requirements.lock` file provides pinned versions for reproducibility. Add upper bounds only when publishing to PyPI.

**pytest.ini NOT migrated:** Simplicity reviewer correctly flagged this as scope creep. `pytest.ini` works fine today. Moving config to `pyproject.toml` is cleanup, not a requirement for pip-installability. Keep `pytest.ini` as-is.

**requirements.txt NOT touched:** Simplicity reviewer correctly flagged adding a comment as busywork. Both files can coexist without confusion.

**Flat layout kept:** Best-practices research noted src layout is preferred for new projects, but migrating existing projects is unnecessary unless there are import issues. Our flat layout works fine.

</details>

#### 4b. Integration verification checklist

Run these commands to verify everything works:

```bash
# 1. Install in editable mode
pip install -e .

# 2. CLI works from any directory
cd /tmp && research-agent --help
cd /tmp && research-agent --cost
cd /tmp && research-agent --list

# 3. Import works
python -c "from research_agent import run_research, list_modes, ResearchResult, ModeInfo; print(list_modes())"
python -c "from research_agent import __version__; print(__version__)"

# 4. Backward compat
cd /path/to/research-agent && python main.py --help

# 5. All tests pass
cd /path/to/research-agent && python -m pytest tests/ -v

# 6. Re-run pip install -e . after adding entry points (editable install gotcha)
pip install -e .
```

<details>
<summary>Research Insights: Editable install gotchas</summary>

**Best-practices research warns:** Entry points don't auto-update in editable mode. After adding `[project.scripts]` to `pyproject.toml`, re-run `pip install -e .` to register the `research-agent` command. This is a known setuptools limitation.

Also: if IDE type checkers (Pylance) struggle with editable installs, try:
```bash
pip install --config-settings editable-mode=strict -e .
```

</details>

---

## File Change Summary

| File | Action | Session |
|------|--------|---------|
| `research_agent/results.py` | Create (ResearchResult + ModeInfo) | 1 |
| `research_agent/agent.py` | Add 6 lines (source tracking + reset) | 1 |
| `tests/test_results.py` | Create | 1 |
| `research_agent/__init__.py` | Rewrite (public API) | 2 |
| `tests/test_public_api.py` | Create | 2 |
| `research_agent/cli.py` | Create (move from main.py) | 3 |
| `main.py` | Simplify to 2-line shim | 3 |
| `tests/test_main.py` | Update import paths | 3 |
| `pyproject.toml` | Create | 4 |

## Known Limitations (Carry Forward to Cycle 19)

- **Stdout noise:** `agent.py` prints ~30 progress lines. Must convert to `logging` module before MCP server. Agent-native review recommends `on_progress` callback pattern.
- **CWD-relative paths:** `REPORTS_DIR`, `RESEARCH_LOG_PATH`, `research_context.md` resolve from CWD. Add `output_dir` parameter to `run_research()` in Cycle 19 for MCP/REST.
- **Version sync:** `__version__` in `__init__.py` and `version` in `pyproject.toml` must be bumped together. Test guards against drift. Switch to `importlib.metadata` dynamic versioning when publishing to PyPI.
- **Agent-native gaps (6.4/10):** No progress callbacks, no `list_reports()` API, no `capabilities()` introspection, minimal metadata in ResearchResult. All planned for Cycle 19.
- **CLI-only features:** `--list` (report listing) and `--open` (open in editor) have no programmatic API equivalents. Add `list_reports()` in Cycle 19.

## References & Research

### Internal References
- Brainstorm: `docs/brainstorms/2026-02-15-cycle-18-pip-installable-package.md`
- Existing `__init__.py`: `research_agent/__init__.py`
- CLI entry point: `main.py:133` (`main()` function)
- Source count: `research_agent/agent.py:391` (`len(evaluation.surviving_sources)`)
- Gate decision: `research_agent/agent.py:376` (`evaluation.decision`)
- Mode config: `research_agent/modes.py` (frozen dataclass with `from_name()` classmethod)
- Error hierarchy: `research_agent/errors.py` (ResearchError base, 5 subclasses)
- Institutional learning: `docs/solutions/architecture/agent-native-return-structured-data.md`
- CLI learning: `docs/solutions/feature-implementation/cli-quality-of-life-improvements.md`
- Security todo: `todos/036-complete-p3-subprocess-open-validate-extension.md`

### External References
- setuptools build_meta docs: https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html
- PyPA packaging guide: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- Editable installs: https://setuptools.pypa.io/en/latest/userguide/development_mode.html
- console_scripts entry points: https://packaging.python.org/en/latest/guides/creating-command-line-tools/
