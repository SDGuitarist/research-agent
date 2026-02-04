# Lessons Learned: Building a Python Research Agent

## 1. Planning Decisions That Saved Time

### Research Before Coding Paid Off

We spent time upfront researching existing solutions (GPT Researcher, LangChain Open Deep Research, STORM) before writing any code. This revealed:

- **Multi-model strategy works**: Use cheaper models for summarization, expensive models for synthesis. We adopted this pattern.
- **Parallel report generation fails**: LangChain learned that generating report sections in parallel produces disjointed results. We avoided this mistake by using single-shot synthesis.
- **Citation tracking is essential**: All three projects emphasized source attribution. We built this in from the start.
- **Token explosion is real**: Research tasks use 15x more tokens than typical chat. We implemented chunking early.

### Constraint Mapping Prevented Scope Creep

Researching rate limits and API constraints before coding helped us:

- Choose DuckDuckGo for development (free) with a clear path to Tavily for production
- Set appropriate timeouts (15s) and concurrency limits (5 max)
- Understand Anthropic's rate limit tiers and plan for them

### Failure Mode Analysis Guided Error Handling

Cataloging failure modes upfront meant we knew exactly what to catch:

- Network: `ConnectionError`, `TimeoutError`, `httpx.ConnectError`
- Search: `DDGSException`, `RatelimitException`
- LLM: `RateLimitError`, `APIError`

Without this research, we would have used bare `except Exception` everywhere.

---

## 2. Bugs and Issues Found During Review

### High Severity

| Issue | Where | Risk | Fix |
|-------|-------|------|-----|
| **SSRF vulnerability** | fetch.py | Attacker could fetch internal resources (`file://`, `http://localhost`) | Added URL validation blocking non-HTTP schemes and private IPs |

### Medium Severity

| Issue | Where | Risk | Fix |
|-------|-------|------|-----|
| Bare `except Exception` | Multiple files | Masks unexpected errors, makes debugging hard | Replaced with specific exception types |
| No concurrency limit | fetch.py | Could overwhelm servers or hit rate limits | Added semaphore with max 5 concurrent requests |
| New AsyncClient per request | fetch.py | Inefficient, no connection reuse | Shared client with connection pooling |
| API key on CLI | main.py | Visible in process list (`ps aux`) | Removed flag, env var only |
| Silent exception swallowing | summarize.py | Failures invisible | Added logging for exceptions from `gather()` |

### Low Severity

| Issue | Where | Fix |
|-------|-------|-----|
| `print()` instead of logging | Multiple | Replaced with `logging` module |
| Unused imports | agent.py | Removed `SearchResult`, `FetchedPage`, etc. |
| Misleading parameter name | agent.py | Renamed `haiku_model` → `summarize_model` |
| Sequential chunk processing | summarize.py | Parallelized with `asyncio.gather()` |
| Imports inside function | extract.py | Moved to top of file |

### Model ID Issues (Runtime)

The original model IDs (`claude-haiku-4-5-20250514`) didn't work. We discovered:

- The API key only had access to `claude-sonnet-4-20250514`
- Older model IDs (`claude-3-5-sonnet-20241022`) returned 404
- Always test with actual API calls early

---

## 3. Patterns Worth Reusing

### Modular File Structure

```
research_agent/
├── errors.py      # Custom exceptions (base + specific)
├── search.py      # Single responsibility: search
├── fetch.py       # Single responsibility: HTTP fetching
├── extract.py     # Single responsibility: content extraction
├── summarize.py   # Single responsibility: LLM summarization
├── synthesize.py  # Single responsibility: report generation
└── agent.py       # Orchestrator that composes the above
```

**Why it works:**
- Each file is testable in isolation
- Easy to swap implementations (e.g., different search provider)
- Clear dependency flow: `search → fetch → extract → summarize → synthesize`

### Dataclass Pipeline

Each stage outputs a typed dataclass that the next stage consumes:

```python
SearchResult → FetchedPage → ExtractedContent → Summary → str (report)
```

**Benefits:**
- Type hints catch errors early
- Easy to inspect intermediate results
- Self-documenting code

### Fallback Chains

```python
# Extract with trafilatura first, fall back to readability
result = _extract_with_trafilatura(page)
if not result or len(result.text) < 100:
    result = _extract_with_readability(page)
```

**When to use:** Any operation where multiple libraries can accomplish the same goal with different tradeoffs.

### URL Validation Pattern

```python
ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}

def _is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return False
    if parsed.hostname.lower() in BLOCKED_HOSTS:
        return False
    # Check private IP ranges...
    return True
```

**Reuse this:** Any time you fetch user-provided URLs.

### Concurrency with Semaphore

```python
async def fetch_urls(urls, max_concurrent=5):
    semaphore = asyncio.Semaphore(max_concurrent)

    async with httpx.AsyncClient(...) as client:
        tasks = [_fetch_single(client, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks)
```

**Benefits:**
- Prevents overwhelming external services
- Reuses connections via shared client
- Easy to tune concurrency limit

### Error Logging in gather()

```python
results = await asyncio.gather(*tasks, return_exceptions=True)

for result in results:
    if isinstance(result, list):
        all_results.extend(result)
    elif isinstance(result, Exception):
        logger.error(f"Task failed: {result}")
```

**Why:** `gather()` with `return_exceptions=True` prevents one failure from canceling all tasks, but you must explicitly handle the exceptions.

---

## 4. Mistakes to Avoid Next Time

### Don't Use Bare Exceptions

```python
# Bad
except Exception:
    return None

# Good
except (ConnectionError, TimeoutError, httpx.ConnectError):
    return None
```

Bare exceptions hide bugs. Always catch specific exceptions.

### Don't Trust User-Provided URLs

Any URL that comes from search results or user input could be:
- `file:///etc/passwd`
- `http://169.254.169.254/` (AWS metadata)
- `http://localhost:8080/admin`

Always validate before fetching.

### Don't Pass Secrets via CLI Arguments

```bash
# Bad - visible in `ps aux`
python main.py --api-key sk-ant-...

# Good - only from environment
export ANTHROPIC_API_KEY=sk-ant-...
python main.py "query"
```

### Don't Ignore Rate Limits

We initially had no concurrency limit on URL fetching. This could:
- Get your IP blocked
- Overwhelm small sites
- Hit API rate limits

Always add throttling for external requests.

### Don't Skip the Code Review

The SSRF vulnerability wasn't in the original implementation plan. It was caught during code review. Even for personal projects, review your own code with fresh eyes.

### Don't Hardcode Model IDs Without Testing

We assumed model IDs like `claude-haiku-4-5-20250514` would work. They didn't. Always:
- Test API calls early with your actual credentials
- Have fallback model options
- Check what models your API key can access

### Don't Mix Output Concerns

We initially had `print()` scattered throughout for progress updates AND error logging. This made it hard to:
- Redirect output properly
- Control verbosity
- Parse logs

Separate user-facing progress from debug logging.

---

## 5. Research Modes Feature (Session 2)

### What We Built

Added three research modes with different depth/cost tradeoffs:

| Mode | Sources | Passes | Report | Cost |
|------|---------|--------|--------|------|
| `--quick` | 3 (2+1) | 2 | ~300 words | ~$0.12 |
| `--standard` | 7 (4+3) | 2 | ~1000 words | ~$0.20 |
| `--deep` | 10+ | 2 | ~2000 words | ~$0.50 |

All modes now use two-pass search with query refinement. Deep mode's refinement uses full summaries (after fetching), while quick/standard use snippets (before fetching) to keep costs the same.

### Planning Before Coding Made Implementation Smooth

We designed the entire feature before writing any code:

1. Defined all three modes with exact parameters
2. Mapped out two-pass search flow with deduplication
3. Specified synthesis prompt changes per mode
4. Designed auto-save with filename format and edge cases
5. Listed failure modes specific to the new functionality

**Result:** Implementation took one pass with zero architectural changes mid-flight. The plan served as a checklist—we just executed it sequentially.

**Contrast with Session 1:** The original implementation required multiple review/fix cycles to catch issues like SSRF and bare exceptions. This time, the upfront design meant fewer surprises.

### The Query Refinement Pattern

Deep mode's second search pass uses a simple but effective pattern:

```python
def refine_query(original_query: str, summaries: list[str]) -> str:
    prompt = f"""Given this research question: "{original_query}"

    And these initial findings:
    {truncated_summaries}

    Generate ONE follow-up search query that:
    - Fills gaps in the initial research
    - Explores a specific angle not yet covered
    - Is 3-8 words, suitable for a search engine

    Return ONLY the query, nothing else."""
```

**Example transformation:**
- Original: `"GraphQL vs REST API design"`
- Refined: `"GraphQL REST API performance benchmarks comparison"`

The refined query found 10 new unique URLs that the original query missed. This pattern is reusable for any multi-pass research system.

### Haiku Model Limitation (API Tier Issue)

We initially planned to use Claude Haiku for query refinement (~$0.001 per call). It failed:

```
Error: model: claude-3-5-haiku-20241022 not found
```

**Root cause:** API key tier doesn't include Haiku access.

**Pragmatic fix:** Fall back to Sonnet for refinement. The cost difference for a 50-token query is negligible (~$0.002 vs ~$0.001), and reliability matters more than micro-optimization.

**Lesson:** Don't optimize for cost before confirming model access. Test API calls with your actual credentials early.

### Review Quality Improved

| Metric | Session 1 | Session 2 |
|--------|-----------|-----------|
| High severity issues | 1 (SSRF) | 0 |
| Medium severity issues | 5 | 2 |
| Low severity issues | 7 | 4 |

The improvement came from:
1. **Upfront design** caught edge cases before they became bugs
2. **Learned patterns** from Session 1 (specific exceptions, empty response checks)
3. **Proactive review request** before the user asked

Issues found in Session 2 review:
- Broad `except Exception` in `refine_query()` → narrowed to specific API errors
- Missing empty response check in synthesis → added explicit check
- Timestamp collision risk → added microseconds
- Unused enum → removed

### Key Decisions That Worked

| Decision | Why It Worked |
|----------|---------------|
| Mutually exclusive CLI flags | `argparse` handles conflicts automatically; cleaner than `--mode quick` |
| Mode as frozen dataclass | Immutable config object, single source of truth for all mode parameters |
| Auto-save only for deep mode | Quick/standard are exploratory; deep is investment worth preserving |
| Graceful pass 2 failure | If refinement or second search fails, continue with pass 1 results |
| Sonnet for refinement | Reliability over micro-savings; one less thing to debug |

---

## 6. Query Refinement for All Modes (Session 2 Continued)

### Extending Two-Pass Search to Quick and Standard

After deep mode proved that query refinement improves results, we extended it to all modes—without increasing costs.

**The key insight:** Quick and standard modes can refine using **search snippets** instead of full summaries. This means:
1. Search with partial budget (2 or 4 sources)
2. Use snippet text to generate refined query (no fetch/summarize cost yet)
3. Search again with remaining budget (1 or 3 sources)
4. Fetch and summarize all results together

**Cost stays the same** because total sources are unchanged—just split across two passes.

### Snippets vs Summaries for Refinement

| Mode | Refines Using | Why |
|------|---------------|-----|
| Quick/Standard | Snippets (before fetch) | Keeps cost identical; snippets are "good enough" |
| Deep | Summaries (after fetch) | Has budget for richer context; better refined queries |

The `refine_query()` function already truncates input to 150 chars, so snippets work just as well as summaries for generating a follow-up query.

### Code Reuse Through Refactoring

Instead of duplicating deep mode's logic, we:
1. Extracted `_research_deep()` for deep mode's existing workflow
2. Created `_research_with_refinement()` for quick/standard's new workflow
3. Both share `refine_query()`, deduplication logic, and the fetch/extract/summarize pipeline

**Lines of code:** +152, -56 = net +96 lines for a significant feature improvement.

### Example Results

**Quick mode before refinement:**
```
Query: "average wedding budget San Diego"
→ 3 results, mostly generic budget articles
```

**Quick mode after refinement:**
```
Original query: "average wedding budget San Diego"
Refined query:  "San Diego wedding cost breakdown by venue type"
→ 3 results, but more specific and diverse sources
```

The refined query found venue-specific pricing data that the original query missed.

### Design Decision: Show Both Queries

Terminal output now displays both queries so users understand what's happening:

```
[1/5] Searching for: average wedding budget San Diego
      Mode: quick (3 sources, 2 passes)
      Original query: average wedding budget San Diego
      Pass 1 found 2 results
      Refined query: San Diego wedding cost breakdown by venue type
      Pass 2 found 1 results (1 new)
      Total: 3 unique sources
```

This transparency helps users understand why results improved and builds trust in the refinement process.

---

## Summary

| Category | Key Takeaway |
|----------|--------------|
| **Planning** | Research existing solutions before coding—learn from their mistakes |
| **Planning** | Design features completely before coding—fewer mid-flight changes |
| **Security** | Validate all external URLs; never pass secrets via CLI |
| **Error Handling** | Catch specific exceptions; log failures from `gather()` |
| **Error Handling** | Always have graceful fallbacks for optional enhancements (pass 2, refinement) |
| **Performance** | Use connection pooling; limit concurrency; parallelize where safe |
| **Architecture** | One file per responsibility; dataclass pipelines; fallback chains |
| **Architecture** | Frozen dataclasses make excellent configuration objects |
| **Architecture** | Extract shared logic into reusable methods when extending features |
| **Testing** | Test API calls early; review code even for personal projects |
| **Testing** | Verify model access before optimizing for specific models |
| **UX** | Show users what's happening (both queries) to build trust in automated processes |
