# Python Research Agent: Research Summary & Plan

## 1. Existing Solutions Analysis

### Projects Reviewed

| Project | Stars | Architecture | License |
|---------|-------|--------------|---------|
| **GPT Researcher** | 25.2k | Planner-Executor-Publisher | Apache-2.0 |
| **LangChain Open Deep Research** | 10.4k | Graph-based Agent Workflow | MIT |
| **STORM (Stanford)** | 27.9k | Simulated Expert Conversations | MIT |

### Patterns That Work Well

1. **Multi-model strategy**: Use cheaper models (Haiku) for summarization/extraction, expensive models (Sonnet) for synthesis
2. **Parallel processing**: Process multiple search results/chunks concurrently with asyncio
3. **Two-phase approach**: Collect and summarize first, then synthesize into final report
4. **Chunking with context**: Split large documents at semantic boundaries, not arbitrary character limits
5. **Citation tracking**: Maintain source attribution throughout the pipeline

### Common Mistakes to Avoid

1. **Hallucinated sources** - GPT Researcher users report fabricated citations
2. **Token explosion** - Research uses 15x more tokens than typical chat (per Anthropic)
3. **Parallel report writing fails** - LangChain found that generating sections in parallel produces disjointed reports; single-shot final synthesis works better
4. **Rate limit handling** - Azure OpenAI users report poor throttling handling even with high limits
5. **PDF/complex content** - PyMuPDFScraper issues with large files, SSL timeouts
6. **GPL contamination** - GPT Researcher has GPL dependencies from PDF processing

---

## 2. Technical Constraints

### Search API Options

| API | Free Tier | Paid Rate | Rate Limit | Notes |
|-----|-----------|-----------|------------|-------|
| **duckduckgo-search** | Unlimited* | N/A | Undocumented | Scraping-based, can be blocked, educational use only |
| **Tavily** | 1,000/mo | $0.008/query | 100 RPM | Built for LLM research, recommended by GPT Researcher |
| **Brave Search** | 2,000/mo | $5/1,000 | 1 req/sec | Own index, reliable free tier |
| **Google Custom Search** | 100/day | $5/1,000 | 10K/day max | Limited, requires setup |

**Recommendation**: Start with `duckduckgo-search` for development, plan migration to Tavily or Brave for production.

### Web Scraping Constraints

**Blocking indicators:**
- 403 = Bot detection (change request characteristics)
- 429 = Rate limit (implement backoff)
- 202 from DuckDuckGo = Rate limited

**Content extraction library ranking (by F1 score):**
1. trafilatura: 0.958 (best overall)
2. newspaper4k: 0.949 (best for news)
3. readability-lxml: 0.922 (most consistent)
4. BeautifulSoup: 0.860 (manual parsing only)

### Anthropic API Constraints

**Rate limits (Tier 1 - default):**
- 50 requests/minute
- 30,000 input tokens/minute
- 8,000 output tokens/minute

**Key optimizations:**
- Prompt caching reduces input cost by 90% (cache hit = $0.30/M vs $3/M for Sonnet)
- Cached tokens don't count toward ITPM limits
- Always stream responses > 1000 tokens
- Use Haiku ($1/M input) for summarization, Sonnet ($3/M) for synthesis

---

## 3. Failure Modes Map

### Critical Failures (Must Handle)

| Category | Failure | Detection | Handling |
|----------|---------|-----------|----------|
| **Network** | Connection timeout | `requests.exceptions.ConnectTimeout` | Retry 3x with exponential backoff |
| **Network** | SSL errors | `ssl.SSLError` | Fallback to http or skip |
| **Search** | Rate limit (429) | Status code 429, `RatelimitException` | Backoff, switch to backup API |
| **Search** | Empty results | Zero results returned | Rephrase query, broaden terms |
| **Scraping** | Bot blocked (403) | Status code 403 | Rotate User-Agent, use proxy |
| **Scraping** | JS-rendered content | Empty body despite 200 | Detect and skip or use Playwright |
| **LLM** | Rate limit (429) | `RateLimitError` | Honor `retry-after` header |
| **LLM** | Context exceeded | `BadRequestError` with context message | Truncate/chunk input |
| **LLM** | Content filtered | `output_blocked` stop reason | Log and report gracefully |

### Non-Critical Failures (Graceful Degradation)

| Category | Failure | Handling |
|----------|---------|----------|
| **Scraping** | Paywall | Skip source, note in report |
| **Scraping** | CAPTCHA | Skip source |
| **Content** | Encoding issues | Try multiple encodings, then skip |
| **Content** | Non-text (PDF, image) | Skip or note limitation |
| **Output** | Missing citations | Generate report with available sources |

---

## 4. Three Approaches

### Approach A: Simple (MVP)

**Architecture:**
```
User Query → DuckDuckGo Search → Fetch Top 5 URLs → Extract Text →
Single Claude Call → Markdown Report
```

**Components:**
- `duckduckgo-search` for search
- `trafilatura` for content extraction
- `httpx` for async HTTP
- Single Anthropic API call with all content

**Tradeoffs:**
| Pros | Cons |
|------|------|
| ~200 lines of code | Limited to ~50K tokens of source content |
| No external dependencies beyond basics | No retry logic for failures |
| Easy to understand and debug | Single point of failure |
| Fast iteration | Poor handling of rate limits |

**Best for:** Personal use, prototyping, learning

---

### Approach B: Moderate (Production-Ready)

**Architecture:**
```
User Query → Search (with fallback) → Parallel URL Fetching →
Chunk Large Documents → Summarize Chunks (Haiku) →
Synthesize Report (Sonnet) → Markdown with Citations
```

**Components:**
- Primary: `duckduckgo-search`, fallback: Brave API
- `trafilatura` + `readability-lxml` fallback chain
- `httpx` with connection pooling and timeouts
- Haiku for per-chunk summarization (parallel)
- Sonnet for final synthesis (streaming)
- Structured error handling with retries

**Tradeoffs:**
| Pros | Cons |
|------|------|
| Handles 100K+ tokens of source material | ~500-800 lines of code |
| Graceful degradation on failures | Requires Anthropic API key management |
| Multi-model cost optimization | More complex debugging |
| Citation tracking | ~$0.05-0.15 per research query |

**Best for:** Side projects, internal tools, moderate reliability needs

---

### Approach C: Robust (Production at Scale)

**Architecture:**
```
User Query → Query Planning (decompose into sub-questions) →
Parallel Research Agents (one per sub-question) →
  Each: Search → Fetch → Extract → Summarize →
Aggregate Results → Deduplicate Sources →
Final Synthesis (Sonnet with streaming) →
Structured Report with Full Citations
```

**Components:**
- Tavily API for search (built for LLM research)
- Multiple extraction backends with automatic fallback
- Playwright for JS-heavy sites
- Redis/SQLite for caching fetched content
- Prompt caching for repeated research patterns
- Structured logging and monitoring
- Rate limit tracking across all APIs

**Tradeoffs:**
| Pros | Cons |
|------|------|
| Handles complex multi-faceted queries | 1500+ lines of code |
| Highly reliable with full retry logic | Tavily costs ($30+/month) |
| Caching reduces repeated costs | Complex deployment |
| Production monitoring | Over-engineered for simple use cases |

**Best for:** Products, APIs serving multiple users, high-reliability requirements

---

## 5. Recommendation: Start with Approach B

### Why Moderate?

1. **Approach A is too fragile** - No error handling means frequent failures in real use. A single 429 or timeout kills the entire request.

2. **Approach C is premature** - Query decomposition and multi-agent coordination add complexity that isn't needed until you've validated the core use case.

3. **Approach B hits the sweet spot:**
   - Handles real-world failures gracefully
   - Multi-model strategy keeps costs reasonable (~$0.10/query)
   - Can process substantial source material (100K+ tokens)
   - Clear upgrade path to Approach C if needed

### Suggested Implementation Order

```
Phase 1: Core Pipeline (Day 1)
├── Basic search with duckduckgo-search
├── URL fetching with httpx + timeouts
├── Content extraction with trafilatura
└── Single Claude call for report generation

Phase 2: Reliability (Day 2)
├── Retry logic with exponential backoff
├── Search API fallback (Brave)
├── Content extraction fallback chain
└── Structured error handling

Phase 3: Optimization (Day 3)
├── Multi-model strategy (Haiku + Sonnet)
├── Parallel chunk processing
├── Streaming output
└── Citation tracking

Phase 4: Polish (Day 4)
├── CLI interface
├── Progress reporting
├── Cost tracking
└── Configuration file
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Search API** | duckduckgo-search (dev), Brave (prod) | Free for development, reliable paid option |
| **HTTP client** | httpx (async) | Better timeout handling than requests, async support |
| **Extraction** | trafilatura primary | Highest F1 score, markdown output support |
| **Summarization model** | claude-haiku-4-5 | 5x cheaper than Sonnet, fast |
| **Synthesis model** | claude-sonnet-4 | Best reasoning for complex synthesis |
| **Concurrency** | asyncio | Native Python, no framework overhead |

---

## Decisions Made

| Question | Decision |
|----------|----------|
| Output format | Markdown only |
| Scope | Single-shot research (no follow-ups) |
| Site preferences | None—use whatever search returns |
| Cost ceiling | ~$0.20/query |
| JavaScript content | Skip JS-rendered pages |

---

## Final Implementation Plan

Based on these decisions, here's the concrete implementation:

### File Structure

```
research-agent/
├── research_agent/
│   ├── __init__.py
│   ├── agent.py          # Main ResearchAgent class
│   ├── search.py         # Search with DuckDuckGo + Brave fallback
│   ├── fetch.py          # Async URL fetching with retries
│   ├── extract.py        # Content extraction (trafilatura + fallback)
│   ├── summarize.py      # Chunk summarization with Haiku
│   ├── synthesize.py     # Report synthesis with Sonnet
│   └── errors.py         # Custom exceptions
├── main.py               # CLI entry point
├── requirements.txt
└── .env.example
```

### Dependencies

```
anthropic>=0.40.0
httpx>=0.27.0
duckduckgo-search>=6.0.0
trafilatura>=1.12.0
readability-lxml>=0.8.0
python-dotenv>=1.0.0
```

### Cost Breakdown (per query, estimated)

| Step | Model | Tokens | Cost |
|------|-------|--------|------|
| Summarize 5 pages × 3 chunks | Haiku | ~15K in, ~3K out | ~$0.03 |
| Synthesize report | Sonnet | ~5K in, ~2K out | ~$0.05 |
| **Total** | | | **~$0.08** |

Well under your $0.20 ceiling, leaving headroom for retries and longer sources.

### Error Handling Strategy

| Failure | Action |
|---------|--------|
| Search rate limit | Wait 5s, retry once, then fail gracefully |
| URL fetch timeout | Skip URL, continue with others |
| URL blocked (403) | Skip URL |
| Empty content | Skip URL |
| LLM rate limit | Honor retry-after, max 3 retries |
| Context too long | Truncate oldest chunks |

### CLI Interface

```bash
# Basic usage
python main.py "What are the best practices for Python async programming?"

# With options
python main.py "query" --max-sources 10 --output report.md
```

---

## Ready to Implement

The plan is complete. Implementation will follow these phases:

1. **Core pipeline** — Search, fetch, extract, single LLM call
2. **Reliability** — Retries, fallbacks, error handling
3. **Optimization** — Multi-model (Haiku + Sonnet), parallel processing
4. **CLI polish** — Progress output, configuration
