# Plan: Multi-Query Decomposition (Feature #1)

> **Status:** Ready for Claude Code review
> **Created:** 2026-02-07
> **Discovery source:** Conversation with Alex — intent, scope, and behavior decisions documented below

---

## STOP — Claude Code Pre-Build Checklist

**Do NOT write any code until you have completed all of the following:**

### 1. Research Best Practices
- Search for how other research agents handle query decomposition (e.g., GPT-Researcher, LangChain research agents, Tavily's own recommendations)
- Look for established patterns for LLM-based query planning/decomposition
- Find any Anthropic cookbook examples or documentation on query decomposition patterns
- Research: what's the most cost-effective way to implement query decomposition with Claude?

### 2. Codebase Review
- Read ALL files in `research_agent/` to understand the full pipeline
- Read `LESSONS_LEARNED.md` and `FAILURE_MODES_CATALOG.md` for known issues
- Read existing tests in `tests/` to understand testing patterns and mocking approach
- Check: does anything in the current architecture conflict with this plan?
- Check: are there any existing patterns we should reuse rather than reinvent?

### 3. Risk Assessment
- What could go wrong with this implementation?
- Could decomposition make simple queries worse? How do we prevent that?
- Are there rate limit implications with parallel sub-query searches?
- Could the context file injection create prompt injection vulnerabilities?
- What happens if decomposition returns bad sub-queries?

### 4. Report Back
- Present your findings to Alex BEFORE writing code
- Propose any adjustments to this plan based on what you learned
- Flag any concerns or conflicts with the existing codebase
- Recommend the build order

---

## Discovery Findings

These decisions come from a structured discovery conversation with Alex.

### What Alex Wants
- The agent should understand the **intent** behind a query, not just the words
- It should automatically break complex queries into focused sub-queries
- It should show its reasoning: the sub-queries it chose and what each found
- A business context file should personalize decomposition without Alex having to explain every query
- "Further research needed" or "insufficient data" responses are considered **failures** — decomposition should prevent most of these
- Quality research is more important than cost, but cost-effectiveness still matters

### What Alex Decided
- **Automatic decomposition** — no manual flags, the agent decides when a query is complex
- **Option A: Decompose upfront only** — no auto follow-up on gaps (that's a separate feature later)
- **Static context file, manually curated** — Alex controls what's in it, not the agent
- **Separate research log** — the agent appends findings to `research_log.md` for Alex to review, but does NOT read it back into prompts
- **Visible reasoning** — show sub-query breakdown and per-query result counts in terminal output
- **Quick mode skips decomposition** — speed over coverage for quick lookups

---

## Problem Statement

Complex queries that span multiple topics fail because a single search term can't cover the intersection.

**Real failure:** "McKinsey-level research on San Diego luxury wedding music market" → 0 of 23 sources passed the relevance gate → "Insufficient Data Found"

**Root cause:** DuckDuckGo and Tavily optimize for simple queries. A compound research question needs to be broken into focused searches that each return relevant results.

---

## Solution Overview

Add a decomposition step BEFORE the search phase. Claude analyzes the query, determines if it's simple or complex, and either passes it through unchanged or breaks it into 2-3 focused sub-queries. Each sub-query goes through the existing two-pass search (search → refine → search). Results merge and deduplicate before entering the existing pipeline.

Additionally, an optional business context file personalizes the decomposition — so the agent understands Alex's market, venues, and goals without being told every time.

### Pipeline Change

```
CURRENT:
  Query → search (2 passes) → fetch → extract → summarize → relevance gate → synthesize

PROPOSED:
  Query → [load context] → decompose → search EACH sub-query (2 passes) → merge/dedup → fetch → extract → summarize → relevance gate → synthesize
```

**Everything after the merge step is unchanged.** The relevance gate, synthesis, and all downstream modules work exactly as before.

---

## New Components

### 1. `research_agent/decompose.py`

**Function:** `decompose_query(client, query, context=None, max_sub_queries=3) -> list[str]`

**Behavior:**
- Reads optional business context from file
- Sends query + context to Claude with a classification prompt
- Claude responds with SIMPLE (returns [original_query]) or COMPLEX (returns 2-3 sub-queries)
- On API failure: falls back to [original_query] — never crashes

**Decomposition prompt should:**
- Classify the query as SIMPLE or COMPLEX
- If COMPLEX, identify the distinct research angles
- Generate 2-3 focused, searchable queries (3-8 words each)
- Use business context (if available) to make sub-queries more specific to Alex's world
- Show brief reasoning about why it decomposed the way it did

**Expected terminal output:**
```
[1/7] Analyzing query...
      This is a market research query with 3 angles:
      → Pricing/cost data for luxury wedding entertainment
      → San Diego venue and market landscape
      → Competitive positioning for live musicians
      Decomposed into 3 sub-queries

[2/7] Searching 3 sub-queries...
      → "luxury wedding entertainment pricing data": 5 results
      → "San Diego premium wedding venue music requirements": 4 results
      → "live musician market rates private events": 6 results
      Total: 12 unique sources (3 duplicates removed)
```

### 2. Business Context File: `research_context.md`

**Location:** Project root (`research-agent/research_context.md`)

**Purpose:** Static file that Alex manually curates. Loaded by decompose.py when present. Agent works fine without it.

**Initial content for Alex:**
```markdown
# Research Context

## Business
Pacific Flow Entertainment — live Spanish guitar, flamenco, 
mariachi, and Latin music for luxury events

## Market
- San Diego luxury weddings and hospitality
- Premium venues: Hotel del Coronado, Grand Del Mar, Gaylord Pacific
- Client profile: high-budget events ($150K+), culturally diverse

## Competitive Position
- 30 years experience, inherited cultural authenticity
- Premium pricing tier
- Differentiator: cultural authenticity + venue expertise

## Research Goals
- Market intelligence and pricing data
- Competitive landscape analysis
- Venue-specific insights
- Client demographic and booking trends
```

**How it's used:** The decomposition prompt includes this as context, so "research the luxury wedding music market" automatically becomes sub-queries about Alex's specific market, not generic wedding music.

**Security:** Content is sanitized before prompt inclusion (same pattern as existing `_sanitize_content()` throughout the codebase).

### 3. Research Log: `research_log.md`

**Location:** Project root (`research-agent/research_log.md`)

**Purpose:** After each run, the agent appends a brief entry:
```markdown
## 2026-02-07 — "luxury wedding music market"
- Mode: standard | Sub-queries: 3 | Sources passed: 6/15
- Key findings: [2-3 sentence summary from synthesis]
- Sub-queries used: [list]
```

**Not read back into prompts.** This is a passive log for Alex to review. When Alex spots valuable patterns, he can manually promote them to `research_context.md`.

---

## Changes to Existing Files

### `agent.py` — Modified

**Both `_research_with_refinement()` and `_research_deep()` get a decomposition step inserted before the first search call.**

The search loop runs per sub-query. For simple queries (decomposition returns 1 query), behavior is identical to current — no regression.

For complex queries, sub-queries search in parallel using `asyncio.gather()` with rate limit delays between them.

After all sub-query searches complete, results merge and deduplicate by URL before entering the existing fetch pipeline.

### `modes.py` — Modified

Add `decompose: bool` field to `ResearchMode`:
- `quick()`: `decompose=False` — skip for speed
- `standard()`: `decompose=True` — benefit from decomposition
- `deep()`: `decompose=True` — always decompose

### `main.py` — No changes

Mode selection already handles configuration. No CLI changes needed.

### All other modules — No changes

`search.py`, `fetch.py`, `extract.py`, `summarize.py`, `relevance.py`, `synthesize.py` — untouched. They already work on lists of results/URLs/summaries and don't care where those lists came from.

---

## Source Budget Strategy

**Don't multiply the source budget — divide it across sub-queries.**

```
Standard mode currently: 6 pass1 + 4 pass2 = 10 raw sources
With 3 sub-queries:      2 pass1 + 2 pass2 per sub-query = 12 raw sources (roughly same budget)
After dedup:             ~8-10 unique sources
After relevance gate:    ~4-7 surviving sources (same as before)
```

Let Claude Code determine the exact per-sub-query source distribution based on best practices research. The goal: roughly the same total API cost, but more diverse sources.

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Simple query ("Python async best practices") | Decomposition returns [original_query], pipeline runs identically to current behavior |
| Decomposition API call fails | Fall back to [original_query] — same pattern as existing `refine_query()` |
| Sub-query returns 0 results | Continue with results from other sub-queries |
| ALL sub-queries return 0 results | Same as current: raise ResearchError |
| Context file missing | Decomposition still works, just less personalized |
| Context file has bad content | Sanitize before prompt inclusion (existing pattern) |
| Duplicate URLs across sub-queries | Deduplicate by URL (existing pattern in agent.py) |
| Rate limits with parallel searches | Stagger with jitter delays (existing pattern in agent.py) |

---

## Success Criteria

- [ ] Simple queries behave exactly as before — zero regression
- [ ] Complex queries decompose into 2-3 focused sub-queries automatically
- [ ] Terminal shows the reasoning: sub-queries chosen and per-query result counts
- [ ] Business context file personalizes decomposition when present
- [ ] Agent works fine without context file
- [ ] The McKinsey wedding query now produces a real report
- [ ] Quick mode skips decomposition entirely
- [ ] API failures in decomposition fall back gracefully
- [ ] All existing tests still pass
- [ ] Research log captures run metadata after each execution
- [ ] Cost increase is reasonable (let Claude Code determine optimal approach)

---

## Files to Create

| File | Type | Purpose |
|------|------|---------|
| `research_agent/decompose.py` | New module | Query analysis and decomposition logic |
| `research_context.md` | New file (project root) | Alex's business context for personalized decomposition |
| `research_log.md` | New file (project root) | Passive run log (append-only, not read by agent) |
| `tests/test_decompose.py` | New tests | Unit tests for decomposition |

## Files to Modify

| File | Change |
|------|--------|
| `research_agent/agent.py` | Add decomposition step before search in both pipeline paths |
| `research_agent/modes.py` | Add `decompose: bool` field to ResearchMode |
| `research_agent/__init__.py` | Export new module if needed |

## Files NOT Modified

`search.py`, `fetch.py`, `extract.py`, `summarize.py`, `relevance.py`, `synthesize.py`, `errors.py`, `main.py`
