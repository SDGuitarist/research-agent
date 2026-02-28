# Lessons Learned: Building a Python Research Agent

This document is the hub for all lessons from 18 development cycles of the research agent. Narrative details live in category files under [`docs/lessons/`](docs/lessons/).

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
| 10 | Analytical depth: business context, 12-section template, batching, structured summaries | Generic templates + context file > hardcoded specifics |
| 11 | Rate limit root cause fix | Concurrency control belongs at the API call layer, not task organization |
| 12 | Quick wins: shared sanitize, parallel sub-queries, context validation | replace_all on substrings corrupts method names; always run tests immediately |
| 13 | Sub-query divergence: prompt + max-overlap validation | Concrete examples (BAD/GOOD) outperform vague instructions; diagnose with real queries before/after |
| 14 | CLI QoL: --cost, --list, --open, filename swap, progress timing | Cost values belong in dataclass (single source of truth); `nargs="?"` needs validation guard |
| 15 | Source-level relevance aggregation | Score the unit you decide on (sources, not chunks); diagnose with real data before fixing |
| 16 | Skeptic pass: draft→skeptic→final pipeline | Multi-pass synthesis catches unsupported claims; `lstrip` strips characters not prefixes — use `removeprefix` |
| 17 | Gap-aware research loop (4 sub-cycles) | Foundation modules first, integration last; four-state result types over None; atomic writes for persistent state |
| 17+ | Real-world research runs (Lodge at Torrey Pines) | Short queries beat complex ones; LinkedIn is the biggest blind spot; "insufficient data" can be the answer |
| 18 | Pip-installable package | Delegate validation to the module that owns the data; wrap, don't refactor |

## Top 10 Patterns

Patterns that recurred across 3+ cycles or prevented entire categories of bugs. Search for these first when facing a similar problem.

| # | Pattern | Cycles | Category File |
|---|---------|--------|---------------|
| 1 | Layered prompt injection defense (sanitize + XML + system prompt) | 4, 6, 9, 12, 14 | [security.md](docs/lessons/security.md) |
| 2 | Additive pattern: new stages layer on, never change downstream | 8-18 | [architecture.md](docs/lessons/architecture.md) |
| 3 | One file per pipeline stage | 1-18 | [architecture.md](docs/lessons/architecture.md) |
| 4 | Frozen dataclasses for configuration | 2-3, 6, 14, 18 | [architecture.md](docs/lessons/architecture.md) |
| 5 | Catch specific exceptions, never bare `except Exception` | 1, 2, 4, 14 | [security.md](docs/lessons/security.md) |
| 6 | Research existing solutions before coding | 1, 7, 8 | [process.md](docs/lessons/process.md) |
| 7 | SSRF protection compounds across cycles | 1, 4, 9, 14 | [security.md](docs/lessons/security.md) |
| 8 | Rate limit at the request level, not the batch level | 10, 11, 14 | [operations.md](docs/lessons/operations.md) |
| 9 | Validate LLM output before using it — plausible ≠ correct | 8, 13, 16 | [architecture.md](docs/lessons/architecture.md) |
| 10 | Live-test integrations before designing around them | 8+, 9 | [operations.md](docs/lessons/operations.md) |

## Category Files

| File | Sections | Topics |
|------|----------|--------|
| [security.md](docs/lessons/security.md) | 7, 14 (security) | SSRF layering, prompt injection, TOCTOU, redirect bypass, sanitize-all-paths |
| [architecture.md](docs/lessons/architecture.md) | 3, 5, 6, 8, 10, 12, 13, 16, 18, 20 | Pipeline design, additive pattern, frozen dataclasses, multi-pass synthesis, typed APIs |
| [operations.md](docs/lessons/operations.md) | 2, 9, 11, 14 (performance), 15, 16 (parallelization), 19 | Rate limiting, fetch cascade, instrumentation, sleep budgets, live-test integrations |
| [process.md](docs/lessons/process.md) | 1, 4, 14 (review methodology), 17, 20 (validation Qs) | Planning, review cadence, testing discipline, prompting strategy, feed-forward |
| [patterns-index.md](docs/lessons/patterns-index.md) | All | Flat searchable table with cycle mappings |

## How to Search

**By pattern:** Open [`patterns-index.md`](docs/lessons/patterns-index.md) and search by keyword.

**By category:** Open the relevant category file above.

**By cycle:** Check the Development History table, then read the corresponding category file section.

**By the learnings-researcher agent:** The agent can grep for tags in the YAML frontmatter of each file.

## Summary

> **Moved to [`docs/lessons/patterns-index.md`](docs/lessons/patterns-index.md)** — searchable table with cycle mappings and category file pointers.
