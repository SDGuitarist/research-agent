# Agent-Native Remediation Plan

**Date:** 2026-02-13
**Source:** Agent-native architecture review
**Status:** Not Started

## Overview

The research agent works well as a CLI tool but is opaque to programmatic callers. An agent calling `research()` gets a markdown string and nothing else — no scores, no progress, no intermediate data. Internally the architecture is clean and composable; it just needs to be exposed.

---

## Phase 1: Structured Return Value (Highest Impact)

**Problem:** `research()` / `research_async()` return `str`. All metadata (scores, source counts, decision, timing) is computed then discarded.

**Fix:** Create a `ResearchResult` dataclass and return it instead of a bare string.

```python
@dataclass
class ResearchResult:
    report: str
    mode: str                      # "quick" | "standard" | "deep"
    query: str
    refined_query: str | None
    decision: str                  # "full_report" | "short_report" | "insufficient_data"
    sources_found: int
    sources_kept: int
    source_scores: list[dict]      # Per-source relevance scores
    elapsed_seconds: float
    decomposition: dict | None
    output_path: str | None
```

**Files to modify:**
- `research_agent/agent.py` — collect metadata throughout pipeline, return `ResearchResult`
- `research_agent/__init__.py` — export `ResearchResult`
- `main.py` — update to use `result.report` for file output and `result` fields for display
- `tests/` — update return value assertions

**Breaking change:** Yes — `research()` return type changes from `str` to `ResearchResult`. Callers need `result.report` to get the markdown. Since this is a young project with no external consumers, this is acceptable.

---

## Phase 2: Progress Callback System

**Problem:** ~40 `print()` calls across `agent.py`, `relevance.py`, `synthesize.py`. Human sees step-by-step progress; programmatic callers see nothing.

**Fix:** Accept an `on_progress` callback in `ResearchAgent.__init__()`.

```python
def __init__(self, ..., on_progress: Callable[[str, dict], None] | None = None):
    self._on_progress = on_progress or self._default_progress

@staticmethod
def _default_progress(event: str, data: dict) -> None:
    # Replicates current print() behavior for CLI users
    if event == "step":
        print(f"\n[{data['step']}/{data['total']}] {data['message']} ({data['elapsed']:.1f}s)")
```

Then replace `print()` calls with `self._emit("step", {...})`.

**Events to emit:**
- `step` — pipeline stage start (step number, total, message, elapsed)
- `search_complete` — search results (count, queries used)
- `fetch_complete` — fetch results (succeeded, failed, cascaded)
- `relevance_scored` — per-source scores (url, score, kept/dropped)
- `decision` — gate result (full_report/short_report/insufficient_data)
- `synthesis_start` — beginning report generation
- `synthesis_token` — streaming token (replaces stdout streaming)

**Files to modify:**
- `research_agent/agent.py` — replace `print()` with `self._emit()`, pass callback to child functions
- `research_agent/relevance.py` — accept callback for score reporting
- `research_agent/synthesize.py` — accept `stream_callback` for token streaming
- `tests/` — test that events fire correctly

**Approach:** Do `agent.py` first (the orchestrator has most of the print calls). Then `synthesize.py` (streaming). Then `relevance.py` (scores). Each can be its own commit.

---

## Phase 3: Export Pipeline Primitives

**Problem:** `__init__.py` only exports `ResearchAgent` and `ResearchMode`. An agent that wants to search, fetch, or score independently must reach into private modules.

**Fix:** Export key primitives from `__init__.py`:

```python
from .agent import ResearchAgent, ResearchResult
from .modes import ResearchMode
from .search import search
from .fetch import fetch_urls
from .extract import extract_all, ExtractedContent
from .summarize import summarize_all
from .relevance import evaluate_sources
from .synthesize import synthesize_report
from .decompose import decompose_query
from .errors import ResearchError, SearchError, SynthesisError, SkepticError
```

**Files to modify:**
- `research_agent/__init__.py` — add exports
- Verify each function has a clean signature (no hidden dependencies on global state)

**No breaking change.** Additive only.

---

## Phase 4: Library-Callable Entry Point

**Problem:** `main()` uses `sys.exit()` in 6 places. An agent calling it programmatically kills the process.

**Fix:** Extract core logic into a `run_research()` function that returns `ResearchResult` and raises exceptions. Keep `main()` as a thin CLI wrapper.

```python
# New function in main.py or agent.py
def run_research(
    query: str,
    mode: str = "standard",
    max_sources: int | None = None,
    output_path: str | None = None,
    on_progress: Callable | None = None,
) -> ResearchResult:
    """Programmatic entry point. Raises ResearchError on failure."""
    ...

# main() becomes:
def main():
    args = parse_args()
    try:
        result = run_research(...)
    except ResearchError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

**Also fix in this phase:**
- `list_reports()` → return `list[dict]`, print in CLI wrapper
- `show_costs()` → return `list[dict]`, print in CLI wrapper
- `append_research_log()` → return `bool` success indicator

**Files to modify:**
- `main.py` — extract `run_research()`, refactor `main()` as wrapper
- `tests/` — test `run_research()` directly

---

## Phase 5: JSON Output + Configurable Paths

**Problem:** Output is always markdown. File paths are hardcoded relative to cwd.

**Fix (JSON):** Add `--format json` flag. Uses `ResearchResult` from Phase 1:

```python
if args.format == "json":
    print(json.dumps(asdict(result), indent=2))
```

**Fix (paths):** Make configurable via constructor or `run_research()` params:

```python
def run_research(
    ...,
    reports_dir: str | None = None,    # Default: "reports"
    log_path: str | None = None,       # Default: "research_log.md"
    context_path: str | None = None,   # Default: "research_context.md"
) -> ResearchResult:
```

**Files to modify:**
- `main.py` — add `--format` arg, path params
- `research_agent/agent.py` — accept path overrides
- `research_agent/context.py` — accept path override

---

## Implementation Order

| Phase | Depends On | Effort | Commits |
|-------|-----------|--------|---------|
| 1. ResearchResult dataclass | None | Medium | 2-3 |
| 2. Progress callbacks | Phase 1 (uses ResearchResult) | Medium-Large | 3-4 |
| 3. Export primitives | None | Small | 1 |
| 4. Library entry point | Phase 1 | Medium | 2-3 |
| 5. JSON output + paths | Phase 1, Phase 4 | Small | 1-2 |

Phase 1 and 3 can be done in parallel. Everything else chains from Phase 1.
