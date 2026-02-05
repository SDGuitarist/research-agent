# Cycle 7 Plan: Search Quality (Minimal Version)

**Project**: Research Agent
**Date**: February 5, 2026
**Cycle**: 7
**Fidelity**: One (focused changes, clear scope, minimal complexity)
**Methodology**: Compound Engineering — Plan (40%) → Work (20%) → Review (40%) → Compound (10%)

---

## Problem Statement

Three issues limit the research agent's effectiveness:

1. **Search provider lock-in**: DuckDuckGo is hardcoded and unreliable for niche topics.
2. **Source budget doesn't account for filtering**: Deep mode attempts 20 sources but only 5-6 survive the relevance gate.
3. **Comparison queries produce biased results**: "X vs Y" queries return sources skewed toward the more popular option.

---

## Solution: Three Minimal Changes

Based on plan review feedback (DHH, Kieran, Simplicity reviewers), this plan was **aggressively simplified** from the original version.

| Change | Lines of Code | Files Modified |
|--------|---------------|----------------|
| Tavily support | ~40 | 1 (search.py) |
| Source budget increase | ~6 | 1 (modes.py) |
| Comparison balance prompt | ~5 | 1 (synthesize.py) |
| **Total** | **~50** | **3** |

---

## 1. Tavily Support (No Abstraction)

### Approach

Add Tavily as a simple function in the existing `search.py`. No Protocol, no provider classes, no new package structure.

### Implementation

```python
# search.py - Add ~40 lines

import os
from tavily import TavilyClient

def search(query: str, max_results: int = 5) -> list[SearchResult]:
    """Search using Tavily if available, otherwise DuckDuckGo."""
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if tavily_key:
        try:
            return _search_tavily(query, max_results, tavily_key)
        except Exception as e:
            logger.warning(f"Tavily failed: {e}, falling back to DuckDuckGo")
    return _search_duckduckgo(query, max_results)


def _search_tavily(query: str, max_results: int, api_key: str) -> list[SearchResult]:
    """Search using Tavily API."""
    client = TavilyClient(api_key=api_key)

    response = client.search(
        query=query,
        max_results=max_results,
        search_depth="basic",
    )

    results = []
    for item in response.get("results", []):
        results.append(SearchResult(
            title=item.get("title", ""),
            url=item["url"],
            snippet=item.get("content", "")[:500],
        ))

    logger.info(f"Tavily returned {len(results)} results")
    return results
```

### Async Wrapper

The existing `search()` is called from async context. Wrap with `asyncio.to_thread()` at the call site in `agent.py`:

```python
# agent.py - modify search call
results = await asyncio.to_thread(search, query, max_results)
```

### Dependencies

```bash
# Add to requirements.txt
tavily-python>=0.3.0
```

### Usage

```bash
# Default: uses DuckDuckGo
python main.py "query"

# With Tavily (just set the env var)
TAVILY_API_KEY=tvly-xxx python main.py "query"
```

No CLI flags. No provider selection. If the key exists, use Tavily. If it fails, fall back to DuckDuckGo.

---

## 2. Adjusted Source Budgets

### Problem

The relevance gate (Cycle 6) filters ~30-50% of sources. Current budgets don't compensate:

| Mode | Attempts | After Gate | User Feedback |
|------|----------|------------|---------------|
| Quick | 3 | 1-2 | "Too fragile" |
| Deep | 20 | 5-6 | "Not comprehensive" |

### Solution

Increase attempt counts to achieve target survivor counts:

```python
# modes.py - Change 6 numbers

QUICK_MODE = ResearchMode(
    name="quick",
    first_pass_results=4,   # was 2
    second_pass_results=2,  # was 1
    # ... rest unchanged
)

STANDARD_MODE = ResearchMode(
    name="standard",
    first_pass_results=6,   # was 4
    second_pass_results=4,  # was 3
    # ...
)

DEEP_MODE = ResearchMode(
    name="deep",
    first_pass_results=12,  # was 10
    second_pass_results=12, # was 10
    # ...
)
```

### Expected Results

| Mode | New Attempts | Target After Gate |
|------|--------------|-------------------|
| Quick | 6 | 3-4 |
| Standard | 10 | 5-6 |
| Deep | 24 | 10-12 |

---

## 3. Comparison Balance Prompt

### Problem

"React vs Svelte" queries return mostly React content because React is more popular. The synthesis then produces a biased report.

### Solution (Simplest)

Add one instruction to the synthesis prompt. Claude is smart enough to balance coverage when told to.

```python
# synthesize.py - Add to synthesis prompt

# At the end of the existing mode_instructions:
BALANCE_INSTRUCTION = """
If this query compares multiple options (e.g., "X vs Y", "which is better"),
ensure balanced coverage of all options mentioned. Include advantages AND
disadvantages for each. If sources heavily favor one option, acknowledge
this limitation rather than presenting biased conclusions.
"""

# In synthesize_report():
full_instructions = f"{mode.synthesis_instructions}\n\n{BALANCE_INSTRUCTION}"
```

### Why This Works

- The relevance gate already filters off-topic sources
- Claude can identify comparison intent from the query
- Balanced synthesis is a prompt engineering problem, not a search problem
- No additional API calls, no query decomposition, no complexity

---

## Implementation Plan

### Day 1: All Three Changes (~2 hours)

**Step 1: Tavily support (30 min)**
1. Add `tavily-python` to requirements.txt
2. Add `_search_tavily()` function to search.py
3. Modify `search()` to try Tavily first
4. Wrap search call with `asyncio.to_thread()` in agent.py
5. Test: `TAVILY_API_KEY=xxx python main.py "test query"`

**Step 2: Source budgets (15 min)**
1. Update numbers in modes.py
2. Run deep mode, verify more sources survive gate

**Step 3: Balance prompt (15 min)**
1. Add BALANCE_INSTRUCTION to synthesize.py
2. Test with "React vs Vue" query
3. Verify report covers both options

**Step 4: Testing (1 hour)**
1. Add test for Tavily function (mocked)
2. Add test for fallback behavior
3. Run full test suite
4. Manual testing with real queries

### Day 2: Review & Document

1. Self-review the changes
2. Update LESSONS_LEARNED.md with Cycle 7 notes
3. Commit and done

---

## Files to Modify

| File | Changes |
|------|---------|
| `requirements.txt` | Add `tavily-python>=0.3.0` |
| `research_agent/search.py` | Add `_search_tavily()`, modify `search()` |
| `research_agent/agent.py` | Wrap search with `asyncio.to_thread()` |
| `research_agent/modes.py` | Increase source budget numbers |
| `research_agent/synthesize.py` | Add BALANCE_INSTRUCTION to prompt |
| `tests/test_search.py` | Add Tavily tests (mocked) |

**No new files created.**

---

## What We're NOT Building

Explicitly excluded based on reviewer feedback:

| Originally Planned | Why Excluded |
|--------------------|--------------|
| SearchProvider Protocol | YAGNI - only 2 providers |
| search/ package (5 files) | Simple function is sufficient |
| MultiProvider class | Try/except inline is clearer |
| `--search-provider` CLI flag | Env var is sufficient |
| comparison.py module | Prompt engineering solves this |
| LLM comparison detection | Regex/prompt is sufficient |
| 5 sub-queries per comparison | Overkill |
| Per-target result tracking | Unused beyond logging |

---

## Success Criteria

| Metric | Before | After |
|--------|--------|-------|
| Deep mode sources after gate | 5-6 | 10-12 |
| Comparison query balance | Biased | Balanced (via prompt) |
| Search reliability | DuckDuckGo only | Tavily + fallback |
| New lines of code | - | ~50 |
| New files | - | 0 |

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Tavily API issues | Low | DuckDuckGo fallback always works |
| Balance prompt ineffective | Low | Can iterate on prompt wording |
| Budget increase raises costs | Medium | User accepted quality>cost tradeoff |

---

## Future Cycles (If Needed)

If the minimal approach proves insufficient:

- **Cycle 8**: Add Exa for semantic search (same pattern: function + fallback)
- **Cycle 8+**: Query decomposition for comparison (if prompt isn't enough)
- **Cycle 8+**: Provider abstraction (if we actually need 3+ providers)

Don't build it until we need it.

---

## References

- [Best Practices Research](../docs/research/2026-02-05-research-agent-best-practices.md)
- [Cycle 6 Relevance Gate](./CYCLE_6_RELEVANCE_GATE_PLAN.md)
- [Tavily API Documentation](https://docs.tavily.com/)
- Plan review feedback: DHH, Kieran, Simplicity reviewers
