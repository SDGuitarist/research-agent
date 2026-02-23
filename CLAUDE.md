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
python3 -m pytest tests/ -v    # 558 tests, all must pass
```

Mock where the name is imported FROM, not where it's used.

## Setup

```bash
pip install -e ".[test]"   # install package + test deps in editable mode
```

## Environment

- Python 3.14
- `.env` must contain: `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`
- `research_context.md` — business context for personalized decomposition
- All models use `claude-sonnet-4-20250514`

## Code Style

- No formatter configured — match surrounding code style
- Imports: stdlib → third-party → local, separated by blank lines
- Type hints on public function signatures; skip for locals and tests

## Git Conventions

- Commit style: `type(scope): description` — e.g. `feat(18-3): extract CLI to cli.py`
- Types: `feat`, `fix`, `docs`, `refactor`, `test`
- Small commits (~50–100 lines, one concern each)
- Always commit before multi-file edits (checkpoint against mid-edit loss)

## Key Conventions

- **Additive pattern**: New pipeline stages layer on without changing downstream modules
- **Three-layer prompt injection defense**: sanitize content + XML boundaries + system prompt
- **Shared sanitization**: `sanitize_content()` in `sanitize.py` — single source of truth
- **Specific exception handling**: Never bare `except Exception`
- **Frozen dataclasses for modes**: All mode parameters in one place

See `LESSONS_LEARNED.md` for development history and detailed findings from each cycle.

## Three Questions (Mandatory)

Every phase of the compound engineering loop MUST end with three questions
answered in its output document before stopping. Do not skip them even if the
session felt straightforward — the "obvious" sessions are where unexamined
assumptions hide.

### Brainstorm and Plan phases

1. **Hardest decision in this session?**
2. **What did you reject, and why?**
3. **Least confident about going into the next phase?**

### Work phase

Append as a `## Three Questions` section at the bottom of HANDOFF.md:

1. **Hardest implementation decision in this session?**
2. **What did you consider changing but left alone, and why?**
3. **Least confident about going into review?**

### Review phase

1. **Hardest judgment call in this review?**
2. **What did you consider flagging but chose not to, and why?**
3. **What might this review have missed?**

### Fix-batched phase

Append as a `## Three Questions` section at the bottom of each batch file:

1. **Hardest fix in this batch?**
2. **What did you consider fixing differently, and why didn't you?**
3. **Least confident about going into the next batch or compound phase?**

### Compound phase

Append as a `## Three Questions` section at the bottom of the solutions document:

1. **Hardest pattern to extract from the fixes?**
2. **What did you consider documenting but left out, and why?**
3. **What might future sessions miss that this solution doesn't cover?**

### Feed-Forward: Read the Previous Phase's Three Questions

Each phase MUST read the `## Three Questions` section from the previous phase's
output before starting its own work. Specifically, read the **"Least confident
about"** answer — that is the previous phase flagging a risk for you.

| Current Phase | Read Three Questions From |
|---------------|--------------------------|
| Plan | Brainstorm (`docs/brainstorms/`) |
| Work | Plan (`docs/plans/`) |
| Review | — (reviews code, not prior phase output) |
| Fix-batched | Review (`docs/reviews/.../REVIEW-SUMMARY.md`) |
| Compound | Fix results (`docs/fixes/.../batchN.md`) |

**How to address it:** Near the top of your output document, add a short
`### Prior Phase Risk` section that:

1. Quotes the previous phase's "Least confident about" answer verbatim.
2. States in one sentence how this phase addresses or accepts that risk.

If the previous phase document has no `## Three Questions` section, note its
absence and proceed normally.

## Session-Closing Handoff (Mandatory)

Before ending ANY session — whether the phase is complete or context is running
low — you MUST update `HANDOFF.md` (project root, create if missing) with:

1. **What was done** this session (commits, files changed, decisions made)
2. **Three questions** answered (per the phase-specific format above)
3. **Next phase** — which phase comes next in the loop
4. **Next-session prompt** — a copy-paste block the user can paste into a fresh
   window to resume exactly where they left off

Format the prompt block like this:

    ### Prompt for Next Session

    ```
    Read [specific file]. [Specific action]. Relevant files: [list].
    ```

If context is running low before the phase is complete, write a **mid-phase
handoff** with the same format but note what's done and what remains.

Do NOT wait for the user to ask. Do NOT skip this because "the session is
almost over." This is the last thing you do before stopping.
