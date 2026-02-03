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

## Summary

| Category | Key Takeaway |
|----------|--------------|
| **Planning** | Research existing solutions before coding—learn from their mistakes |
| **Security** | Validate all external URLs; never pass secrets via CLI |
| **Error Handling** | Catch specific exceptions; log failures from `gather()` |
| **Performance** | Use connection pooling; limit concurrency; parallelize where safe |
| **Architecture** | One file per responsibility; dataclass pipelines; fallback chains |
| **Testing** | Test API calls early; review code even for personal projects |
