# Research Agent — Claude Code Context

## What This Is

A Python CLI research agent for Pacific Flow Entertainment (Alex Guillen's live music business in San Diego). Searches the web, fetches pages, extracts content, and generates structured markdown reports with citations using Claude.

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
├── summarize.py   — Parallel chunk summarization with Claude
├── relevance.py   — Source quality scoring (1-5), gate: full_report/short_report/insufficient_data
├── synthesize.py  — Report generation with mode-specific instructions
├── modes.py       — Frozen dataclass configs: quick/standard/deep
└── errors.py      — Custom exception hierarchy
```

## Pipeline Flow

```
Query → [load context] → decompose → search EACH sub-query (2 passes)
→ merge/dedup → split (prefetched vs needs-fetch) → fetch remaining
→ cascade recover failed URLs (Jina → Tavily Extract → snippet)
→ extract → summarize → relevance gate → synthesize → report
```

Key: Tavily search returns `raw_content` for some results. These skip the fetch+extract steps entirely via `_split_prefetched()`.

## Key Technical Decisions

- **Additive pattern**: New pipeline stages (decomposition, raw_content, cascade) layer on top without changing downstream modules. Fallback is always "behave as before."
- **Three-layer fetch cascade**: Jina Reader (free, works on most sites) → Tavily Extract (domain-filtered, 1 credit/5 URLs) → snippet fallback (`[Source: search snippet]` prefix).
- **Tavily `include_raw_content="markdown"`**: Zero extra cost, bypasses bot protection. Content comes from Tavily's crawl infra, not our IP.
- **Serial sub-query searches**: 2s stagger with jitter to avoid rate limits. Not parallel.
- **Frozen dataclasses for modes**: Immutable configuration objects. All mode parameters in one place.
- **Specific exception handling**: Never bare `except Exception`. Each module catches its own failure types.
- **Three-layer prompt injection defense**: sanitize content + XML boundaries + system prompt instructions.

## Environment

- Python 3.14
- `.env` must contain: `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`
- If `TAVILY_API_KEY` is missing, silently falls back to DuckDuckGo (lower quality, no raw_content)
- `research_context.md` — Alex's business context for personalized query decomposition
- `research_log.md` — Append-only run log (not read by agent)

## Running

```bash
python3 main.py --quick "query"       # 6 sources, fast, no decomposition
python3 main.py --standard "query"    # 10 sources, decomposition, auto-saves
python3 main.py --deep "query"        # 24 sources, 2-pass with full summarize between passes
python3 main.py --standard "query" -v # Verbose: shows all DEBUG/INFO logs
```

## Testing

```bash
python3 -m pytest tests/ -v    # 259 tests, all must pass
```

Tests use `unittest.mock` — mock Anthropic clients, Tavily clients, and search results. Mock where the name is imported FROM, not where it's used.

## Known Limitations

- **The Knot** (Akamai WAF), **Instagram/Facebook** (CAPTCHA/login walls) block everything — cascade can only provide snippet fallback for these.
- **429 rate limit warnings** during deep mode summarization (30K tokens/min tier) — recurring, becoming the next bottleneck.
- **DuckDuckGo fallback** gets zero `raw_content` — all URLs go through direct HTTP fetch + cascade.
- **Quick mode** has only 6 sources — fragile when sites block bots. Intentional speed/cost tradeoff.
- **Anthropic API tier** limits: no Haiku access, Sonnet only. All models use `claude-sonnet-4-20250514`.

## Development History

| Cycle | Feature | Key Lesson |
|-------|---------|------------|
| 1 | Core agent | SSRF vulnerability caught in review |
| 2-3 | Research modes, query refinement | Frozen dataclasses, snippet-based refinement |
| 4 | Security hardening | 16 issues found in review-only cycle |
| 6 | Relevance gate | Async scoring, sanitize all code paths |
| 7 | Tavily + DuckDuckGo fallback | YAGNI — 50 lines beat 300-line abstraction |
| 8 | Query decomposition | Additive pattern, discovery interview |
| 8+ | Tavily raw_content, --verbose | Verify integrations are active; instrument before diagnosing |
| 9 | Fetch cascade (Jina → Tavily Extract → snippet) | Live-test services before designing; one file per stage |

See `LESSONS_LEARNED.md` for detailed findings from each cycle.
