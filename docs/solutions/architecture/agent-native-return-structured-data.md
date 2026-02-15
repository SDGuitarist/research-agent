---
title: "Agent-Native Gap: Return Structured Data, Not Strings"
date: 2026-02-13
category: architecture
tags:
  - agent-native
  - api-design
  - dataclass
  - callbacks
  - composability
module: agent.py, synthesize.py, __init__.py
symptoms: |
  Programmatic callers get only a markdown string; no access to scores, timing,
  decisions, or progress. ~40 print() calls write metadata to stdout then discard it.
  Streaming synthesis hardcodes print(text, end="", flush=True).
severity: medium
summary: |
  CLI-first design returns opaque strings and uses print() for progress. Agents lose
  all pipeline metadata. Fix: structured return types + callback system from day one.
---

# Agent-Native Gap: Return Structured Data, Not Strings

## Problem

The `research()` function in `agent.py` returns a bare `str` -- the final markdown report. But internally, the pipeline computes rich metadata at every step:

| Metadata | Computed in | What happens to it |
|----------|------------|-------------------|
| Sub-query decomposition (SIMPLE/COMPLEX, sub-queries) | `decompose.py` | Printed, discarded |
| Source count per search round | `search.py` | Printed, discarded |
| Relevance scores (1-5 per source) | `relevance.py` | Printed, discarded |
| Gate decision (full_report / short_report / insufficient_data) | `relevance.py` | Printed, discarded |
| Which sources were dropped and why | `relevance.py` | Printed, discarded |
| Timing per pipeline step | `agent.py` | Printed, discarded |
| Token/cost estimates | `agent.py` | Printed, discarded |

A programmatic caller (another agent, a web backend, a test harness) gets the markdown string and zero visibility into what happened inside. To find out why a report is thin, you have to read stdout logs.

Two additional problems:

1. **Streaming is hardcoded.** Three functions in `synthesize.py` use `print(text, end="", flush=True)` to stream tokens. An agent caller cannot capture these tokens or route them elsewhere.

2. **Internals are hidden.** `__init__.py` exports only `ResearchAgent` and `ResearchMode`, hiding 13 composable modules (`decompose`, `search`, `fetch`, `cascade`, `extract`, `sanitize`, `summarize`, `relevance`, `synthesize`, etc.) that agents could use independently -- for example, running just `decompose` + `search` without synthesis.

## Root Cause

CLI-first thinking. When you build for a human at a terminal:

- `print()` is the natural progress channel -- you see it immediately
- The return value is "just the output" -- a string you write to a file
- You don't export internals because the CLI is the only entry point

This works fine for `python3 main.py --deep "query"`. It breaks the moment another piece of code calls `research()` and needs to make decisions based on what happened (retry if insufficient_data, surface scores in a UI, chain into another agent's context).

## Solution (Planned)

### 1. Return a `ResearchResult` dataclass

```python
@dataclass(frozen=True)
class ResearchResult:
    report: str                          # The markdown report (what we return today)
    gate_decision: str                   # "full_report" | "short_report" | "insufficient_data"
    sources_found: int                   # Total sources before filtering
    sources_used: int                    # Sources that survived relevance gate
    source_scores: list[dict]            # [{url, title, score, dropped, reason}, ...]
    decomposition: dict                  # {classification, sub_queries, original_query}
    timing: dict[str, float]             # {"decompose": 1.2, "search": 3.4, ...}
    mode: str                            # "quick" | "standard" | "deep"
```

`research()` changes from `-> str` to `-> ResearchResult`. CLI callers use `result.report`. Agent callers inspect whatever they need.

### 2. Replace `print()` with `on_progress` callback

```python
async def research(
    query: str,
    mode: ResearchMode = STANDARD,
    on_progress: Callable[[str, dict], None] | None = None,
) -> ResearchResult:
    ...
    _emit(on_progress, "decompose_complete", {"classification": "COMPLEX", "sub_queries": [...]})
    _emit(on_progress, "search_complete", {"sources_found": 14})
    _emit(on_progress, "relevance_complete", {"gate": "full_report", "survival_rate": 0.53})

def _emit(callback, event: str, data: dict):
    if callback:
        callback(event, data)
```

The CLI passes a callback that prints. Agents pass a callback that collects, routes, or ignores. No callback = silent.

### 3. Add `stream_callback` to synthesis functions

```python
async def synthesize_report(
    ...,
    stream_callback: Callable[[str], None] | None = None,
):
    for token in response:
        if stream_callback:
            stream_callback(token)
```

CLI passes `lambda t: print(t, end="", flush=True)`. Agents pass their own handler or `None` for buffered output.

### 4. Export pipeline primitives from `__init__.py`

```python
from research_agent.decompose import analyze_query
from research_agent.search import search_sources
from research_agent.relevance import evaluate_sources
from research_agent.synthesize import synthesize_report
# ... etc.
```

This lets agents compose custom pipelines: decompose a query without searching, search without synthesizing, or re-run relevance with different thresholds.

## Prevention

Design checklist for any pipeline function:

1. **Every function that computes metadata should return it.** If you compute a score, a decision, or a timing -- put it in the return value. Even if the caller ignores it today.

2. **Never `print()` in library code.** Use a callback with `print()` as the default. This costs one extra parameter and zero behavioral change for CLI users.

3. **Export composable primitives, not just the top-level workflow.** If a module does something useful on its own, make it importable. Don't force callers through the full pipeline to access one step.

4. **Test the return type, not stdout.** If your tests assert on captured stdout, that's a sign the data should be in the return value instead.

## Key Lesson

Return structured data from day one, even if the CLI only prints part of it. Use callbacks instead of `print()` in library code. This is much cheaper to build from scratch than to retrofit later -- retrofitting means changing every call site, updating every test that captures stdout, and handling the backward compatibility of a new return type.

The heuristic: if you `print()` something and then throw it away, future-you (or future-agent) will need it.

## Related

- `research_agent/agent.py`: Current `research()` function returning `str`
- `research_agent/synthesize.py`: Three streaming functions with hardcoded `print()`
- `research_agent/__init__.py`: Current exports (only `ResearchAgent`, `ResearchMode`)
- Cycle 15 (source-level relevance): Example of metadata that should be in return values
