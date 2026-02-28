---
title: Architecture Lessons
category: architecture
tags: [pipeline, additive-pattern, dataclass, decomposition, multi-pass, typed-api]
cycles: [1, 2-3, 6, 8, 9, 10, 12, 16, 18]
---

# Architecture Lessons

Pipeline design, the additive pattern, frozen dataclasses, multi-pass synthesis, and typed APIs. These lessons shaped the research agent's modular architecture.

## Patterns Worth Reusing (Cycle 1)

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

**Benefits:** Type hints catch errors early, easy to inspect intermediate results, self-documenting code.

### Fallback Chains

```python
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
    return True
```

### Concurrency with Semaphore

```python
async def fetch_urls(urls, max_concurrent=5):
    semaphore = asyncio.Semaphore(max_concurrent)
    async with httpx.AsyncClient(...) as client:
        tasks = [_fetch_single(client, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks)
```

### Error Logging in gather()

```python
results = await asyncio.gather(*tasks, return_exceptions=True)
for result in results:
    if isinstance(result, list):
        all_results.extend(result)
    elif isinstance(result, Exception):
        logger.error(f"Task failed: {result}")
```

`gather()` with `return_exceptions=True` prevents one failure from canceling all tasks, but you must explicitly handle the exceptions.

## Research Modes Feature (Cycles 2-3)

### Planning Before Coding Made Implementation Smooth

We designed the entire feature before writing any code. **Result:** Implementation took one pass with zero architectural changes mid-flight.

### The Query Refinement Pattern

Deep mode's second search pass uses summaries for refinement; quick/standard modes use snippets (cheaper, same pass2 budget). The `refine_query()` function is shared across all modes.

### Frozen Dataclass for Modes

Mode as frozen dataclass = immutable config object, single source of truth for all mode parameters.

## Query Refinement for All Modes (Cycles 2-3)

### Snippets vs Summaries for Refinement

| Mode | Refines Using | Why |
|------|---------------|-----|
| Quick/Standard | Snippets (before fetch) | Keeps cost identical |
| Deep | Summaries (after fetch) | Has budget for richer context |

### Code Reuse Through Refactoring

Both `_research_deep()` and `_research_with_refinement()` share `refine_query()`, deduplication logic, and the fetch/extract/summarize pipeline.

### Design Decision: Show Both Queries

Terminal output now displays both queries so users understand what's happening. **Pattern:** Transparency builds trust in automated processes.

## Source Relevance Gate (Cycle 6)

### What We Built

A quality gate between summarization and synthesis that scores each source's relevance:

```
Summaries → [Relevance Gate] → Full Report / Short Report / Insufficient Data
```

### Plan-to-Code Mismatches Are Inevitable

The plan referenced `config.py`, but the actual file was `modes.py`. **Lesson:** Always validate plans against the actual codebase before implementing.

### Sync vs Async Consistency Matters

New components in an async pipeline should be async. Parallel scoring is ~7x faster than sequential with 7 sources.

### Duplicate Code Creeps In During Feature Addition

After implementing the relevance gate, both research methods had nearly identical 40-line blocks. **Fix:** Extract `_evaluate_and_synthesize()` helper.

### Validation Gaps Cause Cryptic Errors

Missing validation for `min_sources_short_report >= 1` would cause a `SynthesisError` with no mention of the real cause. **Pattern:** Validate configuration values that would cause confusing errors downstream.

### Mode Instructions: Append, Don't Replace

```python
# Bad: Loses mode-specific style guidance
if limited_sources:
    mode_instructions = "Write a shorter report..."

# Good: Preserves mode style + adds constraint
if limited_sources:
    mode_instructions = f"{mode_instructions} Given limited sources, write a shorter report..."
```

### Magic Numbers Require Future-You Context

If a number isn't obvious, name it. `INSUFFICIENT_RESPONSE_TIMEOUT = 30.0` beats `timeout=SCORING_TIMEOUT * 2`.

> Cross-reference: See [security.md](security.md) for the sanitization consistency lesson from this cycle.

## Query Decomposition (Cycle 8)

### The Additive Pattern: Never Make Simple Queries Worse

The most important design decision was making decomposition **additive** to the existing search, not a replacement:

```python
# Step 1: Search the original query (baseline — always runs)
pass1_results = await asyncio.to_thread(search, query, self.mode.pass1_sources)

# Step 2: Sub-queries ADD unique sources (only if complex)
if decomposition and decomposition["is_complex"]:
    for sq in sub_queries:
        sq_results = await asyncio.to_thread(search, sq, per_sq_sources)
        new = [r for r in sq_results if r.url not in seen_urls]
        pass1_results.extend(new)
```

**Why additive beats replacement:** For simple queries, decomposition returns `[original_query]` and the pipeline is identical to pre-decomposition behavior. No regression possible. Budget stays flat.

### Multi-Topic Queries Fail — Decompose Into Components

"McKinsey-level research on San Diego luxury wedding music market" → 0 sources passed. Decomposed into sub-queries → 4+ sources → full report.

### Sub-Query Validation Prevents Bad Searches

Word count (2-10 words), semantic overlap check, duplicate detection (>70% word overlap), maximum 3 sub-queries. **Lesson:** Always validate LLM-generated structured output before using it.

### Business Context Personalization

`research_context.md` gives decomposition domain knowledge. Content is sanitized with `sanitize_content()` before prompt inclusion.

### Graceful Fallback Is Non-Negotiable

Every new step must fall back gracefully. The fallback for a failed enhancement is always "do what you did before the enhancement existed."

## Fetch Cascade Fallback (Cycle 9)

### One File Per Pipeline Stage

The cascade lives in `cascade.py`, following the established pattern. Different failure modes, different dependencies, different testing needs.

### Return Existing Types — Zero Downstream Changes

The cascade returns `ExtractedContent`, the same dataclass used by `extract.py`. No new types, no adapters, no downstream changes.

### Inline Markers Beat Structured Metadata (YAGNI)

For snippet fallback: `[Source: search snippet]` prefix. The LLM reads text; it doesn't query fields.

## Analytical Depth (Cycle 10)

### Generic Templates Beat Hardcoded Specifics

The 12-section template is completely generic — no business specifics baked in. The template defines structure; the context file provides specifics at runtime.

### Business Context Flows Through, Not Into, the Pipeline

Context is loaded once, passed as a parameter to `synthesize_report()`. Only sections 9-10 reference it — factual sections remain objective.

### Structured Summaries Give Synthesis Better Raw Material

Deep mode uses structured extraction (FACTS / KEY QUOTES / TONE) instead of free-form summaries. Match the summarization format to what synthesis needs.

### 12-Section Template Verification

The benchmark produced a report with all 12 sections populated. The template's "omit if no data" instruction worked correctly.

## Quick Wins (Cycle 12)

### Deduplicate `_sanitize_content`

Extracted into `research_agent/sanitize.py` as shared public utility. **Bug:** `replace_all` of `_sanitize_content` → `sanitize_content` corrupted test method names (`test_sanitize_content` → `testsanitize_content`). Caught by comparing collected test count.

> Cross-reference: See [operations.md](operations.md) for the parallelization sub-section from this cycle.

### Business Context Validation + Regeneration

LLM instructions are requests, not guarantees. Added post-synthesis validation: check sections 9-10 for business context keywords, regenerate only those sections if missing. A targeted regeneration for 2 sections is much cheaper than re-running the full pipeline.

## Adversarial Verification Pipeline (Cycle 16)

### Multi-Pass Synthesis: Draft → Skeptic → Final

Single-pass synthesis has no mechanism to challenge unsupported claims. The skeptic pipeline separates generation from evaluation:

| Lens | What It Catches |
|------|----------------|
| **Evidence Alignment** | Claims tagged SUPPORTED/INFERRED/UNSUPPORTED |
| **Timing & Stakes** | Misweighted urgency |
| **Strategic Frame** | Wrong problem being solved |

Standard mode: combined call. Deep mode: 3 sequential agents with cumulative pressure.

### Stage-Appropriate Context Slicing

Business context only flows to sections 9-12/13 (draft has sections 1-8 without context). Prevents business context from coloring factual sections.

### The `lstrip` vs `removeprefix` Bug

```python
"## Hello".lstrip("# ")   # → "ello" (strips characters from a set — WRONG!)
"## Hello".removeprefix("## ")  # → "Hello" (removes exact prefix — CORRECT)
```

Always use `removeprefix()` for known prefixes.

## Pip-Installable Package (Cycle 18)

### Validation Ownership: Don't Duplicate What Another Module Defines

```python
# Bad: duplicated knowledge
_VALID_MODES = frozenset({"quick", "standard", "deep"})  # in __init__.py

# Good: delegate to the owner, translate the exception
try:
    research_mode = ResearchMode.from_name(mode)
except ValueError:
    raise ResearchError(f"Invalid mode: {mode!r}. ...")
```

### Additive Migrations: Wrap, Don't Refactor

Wrap existing internals with thin public functions. Move code, don't rewrite it. Zero regression risk by construction.

### Public APIs: Return Typed Objects, Not Dicts

`ModeInfo` frozen dataclass costs 8 lines and provides IDE autocomplete, type checking, and immutability. If your codebase has a pattern, follow it.

### Library Functions Should Not Have Side Effects

`run_research()` does NOT call `load_dotenv()`. The caller owns their environment. Validate env vars up front (fail-fast).

### Private Attr Access as Internal Contract

`run_research()` reads `agent._last_source_count`. Private attr access is acceptable when caller is in the same package, the contract is documented and tested, and the alternative adds more complexity.

### Convert New Data Sources to Existing Intermediate Types

Convert at the boundary — everything downstream works without modification. Same principle from `_split_prefetched()` (Cycle 8+) and cascade (Cycle 9).

### Agentic Browsers Bypass Bot Detection

Agentic browsers (controlling real browser sessions with saved login credentials) bypass bot detection and auth walls the fetch pipeline cannot. Complement the pipeline for authenticated sources like LinkedIn.
