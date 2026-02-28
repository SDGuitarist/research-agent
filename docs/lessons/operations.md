---
title: Operations Lessons
category: operations
tags: [rate-limiting, fetch, instrumentation, sleep-budget, live-testing, tavily, jina]
cycles: [1, 7, 8+, 9, 11, 12, 17+, post-10]
---

# Operations Lessons

Rate limiting, fetch cascade, instrumentation, sleep budgets, and live-test integrations. These lessons keep the research agent reliable in production.

## Bugs and Issues Found During Review (Cycle 1)

### High Severity

| Issue | Where | Risk | Fix |
|-------|-------|------|-----|
| **SSRF vulnerability** | fetch.py | Attacker could fetch internal resources | Added URL validation |

### Medium Severity

| Issue | Where | Risk | Fix |
|-------|-------|------|-----|
| Bare `except Exception` | Multiple files | Masks unexpected errors | Replaced with specific exception types |
| No concurrency limit | fetch.py | Could overwhelm servers | Added semaphore with max 5 |
| New AsyncClient per request | fetch.py | No connection reuse | Shared client with connection pooling |
| API key on CLI | main.py | Visible in process list | Removed flag, env var only |
| Silent exception swallowing | summarize.py | Failures invisible | Added logging for exceptions from `gather()` |

### Model ID Issues (Runtime)

The original model IDs didn't work — the API key only had access to `claude-sonnet-4-20250514`. Always test with actual API calls early.

> Cross-reference: See [security.md](security.md) for SSRF doctrine from the Cycle 4 security hardening review.

## Search Quality Improvements (Cycle 7)

### Aggressive Simplification Beats Over-Engineering

The original Cycle 7 plan included a `SearchProvider` Protocol with 5 new files, `MultiProvider` class, and CLI flag. Three reviewers independently said: **YAGNI.**

**Simplified version:** ~50 lines instead of ~300. Same functionality. Zero new files. One function (`_search_tavily`) added to existing `search.py`.

### Environment Variables Beat CLI Flags for Optional Features

API keys shouldn't be in command history. No code changes needed — just `os.environ.get()`. Fallback is automatic.

### Prompt Engineering Often Beats Code

Comparison query bias had two solutions: complex query decomposition + merging, or a balance instruction in the synthesis prompt. The prompt instruction won — zero API calls, no detection logic, easier to iterate.

### Source Budgets Must Account for Filtering

The relevance gate filters 30-50% of sources. Original budgets didn't compensate. **Fix:** Increase attempts to achieve target survivors.

### Async Wrapping for Sync Libraries

Use `asyncio.to_thread()` for the Tavily client (synchronous) in the async pipeline. Also for CPU-bound operations that would block.

### Mocking Path Must Match Import Location

```python
# Bad - module doesn't have TavilyClient at top level
with patch("research_agent.search.TavilyClient"):

# Good - mock where it's actually imported from
with patch("tavily.TavilyClient"):
```

## Tavily Raw Content & Pipeline Instrumentation (Cycle 8+)

### The Integration That Was Built But Never Activated

Tavily search code existed since Cycle 7 but `TAVILY_API_KEY` was never added to `.env`. Every run silently fell back to DuckDuckGo.

**Lesson:** Verify integrations are actually active, not just built. If a feature has a fallback path, log when the fallback activates.

### Instrument Before Diagnosing

Adding `--verbose` made the real bottleneck visible in one run. The fetch stage was the bottleneck, not relevance scoring.

**Lesson:** A `--verbose` flag costs 11 lines and saves hours of misdiagnosis.

### include_raw_content: Zero Cost, Maximum Impact

Tavily's `include_raw_content="markdown"` parameter returns full cleaned page content at the same credit cost. Content comes from Tavily's crawl infrastructure, not our IP.

**Before:** 1/8 pages with content → short_report. **After:** 4/8 pages → full_report.

**Lesson:** Before building complex fallback chains, check if your existing provider has a parameter you're not using.

### Fetch Failures Were the Primary Bottleneck

| Pipeline Stage | Failure Rate | Impact |
|---------------|-------------|--------|
| Search | ~0% | Reliably return URLs |
| **Fetch** | **50-88%** | Bot blocks, paywalls, Cloudflare |
| Extract | ~5% | Occasional HTML parsing failures |
| Relevance | Working as designed | Correct scoring, starved of input |

**Lesson:** When a downstream stage appears broken, check if upstream is starving it of input.

## Fetch Cascade (Cycle 9)

### Live-Test Services Before Designing the Cascade

| Service | Standard sites | WeddingWire | The Knot | Instagram | GigSalad |
|---------|---------------|-------------|----------|-----------|----------|
| Direct HTTP | Partial | Blocked | Blocked | Blocked | Blocked |
| Tavily raw_content | Partial | Empty | Empty | Empty | Works |
| **Jina Reader** | **Works** | **Works** | Blocked | Blocked | Works |
| Tavily Extract | Works | Untested | Blocked | Blocked | Works |
| Snippet | Available | Available | Available | Available | Available |

**Jina Reader is the highest-value free tool.** Don't design fallback chains from documentation — build a compatibility matrix from live tests.

### Domain Filter for Tavily Extract

Restrict expensive API calls to high-value domains where the data is worth the cost. `frozenset` for immutable O(1) lookup.

### Not All Fetch Failures Are Bot Blocks

Check HTTP status codes (404 vs 403 vs timeout) before escalating to more aggressive fetching.

### Live-Test Before Committing

Jina Search required an API key (not free as assumed). Live testing saved wasted work.

## Rate Limit Root Cause Fix (Cycle 11)

429 errors were caused by **chunk fan-out** in `summarize_content` (`asyncio.gather` firing all chunks per source in parallel), not batch size. Batch size reductions from 12→5 treated the symptom.

**Fix:** `MAX_CONCURRENT_CHUNKS=3` semaphore wrapping leaf-level `summarize_chunk` calls. Application-level 429s dropped from ~30 to 1.

**Key Lesson:** Always place concurrency control at the API call layer, not the task organization layer. For any rate-limited API, start with a semaphore where the actual API calls happen.

## Quick Wins: Parallelization (Cycle 12)

Sub-query searches were serial with a 2-2.5s stagger (3 sub-queries = 6-7.5s of pure sleep). Replaced with `asyncio.gather` bounded by `asyncio.Semaphore(2)`.

**Lesson:** When serial delays exist purely for rate-limit avoidance, a semaphore preserves safety while allowing overlap.

> Cross-reference: See [architecture.md](architecture.md) for the dedup and context validation sub-sections from this cycle.

## Codebase Review: Performance Findings (Post-Cycle 10)

| # | Finding | Impact | File |
|---|---------|--------|------|
| 1 | Chunk fan-out bypasses batch-level rate limiting | Root cause of 429 errors | `summarize.py:192-205` |
| 2 | Serial sub-query searches with 2-2.5s stagger | 6-7.5s wasted per query | `agent.py:317-329` |
| 3 | `extract_all` is sync/CPU-bound, blocks event loop | Several seconds blocked | `agent.py:370, 454, 510` |
| 4 | `refine_query` uses sync Anthropic client without `to_thread` | 1-3s event loop block | `agent.py:333, 488` |
| 5 | Blocking `socket.getaddrinfo` in async context | Redundant blocking per URL | `fetch.py:104-128` |
| 6 | TavilyClient instantiated per call | ~100-300ms wasted | `search.py:85-87` |
| 7 | String concatenation `+=` in streaming loop is O(n²) | Minor | `synthesize.py:155-166` |
| 8 | `_load_context()` reads file twice per invocation | Negligible | `decompose.py:136` |

**Wall time estimate for standard mode:** ~18 seconds in deliberate `sleep` calls alone. Parallelizing sub-queries and fixing chunk fan-out could save 10-15 seconds.

**Key Lessons:**
- Deliberate sleep calls can account for more wall time than actual computation — audit sleep budgets periodically
- `replace_all` on substrings corrupts identifiers — always check test count after refactoring

> Cross-reference: See [security.md](security.md) for security findings. See [process.md](process.md) for review methodology.

## Real-World Research Runs (Cycle 17+)

### Query Complexity vs. Relevance Scoring

Complex queries pull in irrelevant sources, which the relevance scorer drops. **Rule of thumb:** Keep queries under ~15 words. The decomposer handles complexity; the initial query handles precision.

### Business Template Generates Filler for Factual Questions

The 12-section template is optimized for competitive intelligence. Factual questions like "What are the leadership changes?" produce filler in irrelevant sections.

### LinkedIn: The Agent's Biggest Blind Spot

LinkedIn blocks scrapers, Jina Reader, and Tavily Extract. The agent's report can actively contradict reality when key information lives behind walled gardens.

### Guest Reviews Are Hard to Find Programmatically

Review sites (TripAdvisor, Yelp, Google, OpenTable) are heavily bot-protected.

### The Agent Finds Public Record; Humans Find Ground Truth

The research agent excels at aggregating publicly reported facts. For real-time organizational intelligence, the most valuable sources are authenticated platforms and insider knowledge.

### "Insufficient Data" Can Be the Answer

When the research question is "does X currently exist?" and the web has zero evidence of it, `insufficient_data` is the correct, strategically useful verdict. Absence of evidence can be evidence of absence when the topic is something that would normally be advertised publicly.

### Entity Disambiguation

Near-identical entity names fool the relevance scorer. "The Lodge at Torrey Pines" (resort) vs "Torrey Pines Lodge" (state reserve) both pass as relevant.
