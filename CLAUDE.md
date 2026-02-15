# Research Agent — Claude Code Context

## What This Is

A Python CLI research agent for Pacific Flow Entertainment. Searches the web, fetches pages, extracts content, and generates structured markdown reports with citations using Claude.

## Architecture

```
main.py (CLI entry point)
research_agent/
├── agent.py       — Orchestrator: decomposes, searches, fetches, cascades, summarizes, synthesizes
├── decompose.py   — Query analysis: SIMPLE/COMPLEX classification, sub-query generation
├── search.py      — Tavily (primary) + DuckDuckGo (fallback), query refinement
├── fetch.py       — Async HTTP fetching with SSRF protection, UA rotation
├── cascade.py     — Three-layer fallback: Jina Reader → Tavily Extract → snippet
├── extract.py     — Content extraction: trafilatura + readability-lxml fallback
├── sanitize.py    — Shared content sanitization (prompt injection defense)
├── summarize.py   — Batched chunk summarization with Claude
├── relevance.py   — Source quality scoring (1-5), gate: full_report/short_report/insufficient_data
├── synthesize.py  — Report generation with mode-specific instructions + business context validation
├── context.py     — Business context loading (search, synthesis, full slices)
├── skeptic.py     — Adversarial verification: evidence, timing, framing agents
├── modes.py          — Frozen dataclass configs: quick/standard/deep (includes model)
├── context_result.py — Three-way context result (loaded/empty/not_configured)
├── cycle_config.py   — Research cycle parameters (TTL, max gaps, model)
├── safe_io.py        — Atomic file writes with tempfile + rename
├── token_budget.py   — Token counting and priority-based budget pruning
├── schema.py         — Gap data model, YAML parser, validation, cycle detection
├── state.py          — Gap state transitions (mark_verified, mark_checked, save)
├── staleness.py      — Staleness detection, batch selection, audit logging
└── errors.py         — Custom exception hierarchy
```

## Running

```bash
python3 main.py --quick "query"       # 4 sources, fast
python3 main.py --standard "query"    # 10 sources, auto-saves
python3 main.py --deep "query"        # 12 sources, 2-pass with full summarize
python3 main.py --standard "query" -v # Verbose logging
python3 main.py --cost                # Show estimated costs
python3 main.py --list                # List saved reports
```

## Testing

```bash
python3 -m pytest tests/ -v    # 385 tests, all must pass
```

Mock where the name is imported FROM, not where it's used.

## Environment

- Python 3.14
- `.env` must contain: `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`
- `research_context.md` — business context for personalized decomposition
- All models use `claude-sonnet-4-20250514`

## Key Conventions

- **Additive pattern**: New pipeline stages layer on without changing downstream modules
- **Three-layer prompt injection defense**: sanitize content + XML boundaries + system prompt
- **Shared sanitization**: `sanitize_content()` in `sanitize.py` — single source of truth
- **Specific exception handling**: Never bare `except Exception`
- **Frozen dataclasses for modes**: All mode parameters in one place

See `LESSONS_LEARNED.md` for development history and detailed findings from each cycle.
