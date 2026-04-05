---
cycle: 28
title: "Relevance & Source Quality Gates"
brainstorm: "docs/brainstorms/2026-04-05-cycle-28-relevance-cutoff-brainstorm.md"
roadmap: "docs/research/2026-03-09-entropy-fixes-roadmap.md"
feed_forward:
  risk: "Snippet tier detection mechanism — how to set source_tier on Summary without text-prefix fragility"
  verify_first: true
---

# Cycle 28 Plan: Relevance & Source Quality Gates

**Date:** 2026-04-05
**Sessions:** 3

## Enhancement Summary

**Deepened on:** 2026-04-05
**Agents used:** architecture-strategist, spec-flow-analyzer, kieran-python-reviewer, learnings-checker (3 solution docs)

### Key Improvements from Deepening
1. **Type safety:** Use `Literal["full", "snippet"]` for `source_tier` instead of bare `str` — catches typos at type-check time
2. **Named constant:** `SNIPPET_SCORE_CAP = 3` in `relevance.py` instead of magic number
3. **Score cap robustness:** Cap must cover ALL exit paths in `score_source()`, not just happy-path parse
4. **Haiku borderline warning:** Cutoff raise from 3→4 amplifies Haiku's known aggressive scoring at the boundary (Cycle 21 solution doc)
5. **Surviving source URLs:** `generate_insufficient_data_response()` must pass surviving sources — confirmed as a required change, not optional
6. **A/B test additions:** Add 3 high-risk query types (aggregator-heavy, person-specific, very recent events)

### Known Limitations (Accepted)
- Quick-mode `short_report` can be built from snippet-only sources — deferred to Cycle 29 evidence-tier labeling
- `no_new_findings` at cutoff=4 when all sources score exactly 3 is a semantic shift — document but don't change gate logic

## Prior Phase Risk

> "The snippet tier detection mechanism during summarization. Currently `summarize_content()` receives `ExtractedContent` objects, but snippet fallback tags content with a text prefix (`[Source: search snippet]`). To set `source_tier="snippet"` on `Summary`, we need to either: (a) detect the text prefix in `summarize_content()` and propagate, or (b) add a field to `ExtractedContent` and thread it."

**Resolved.** Option (b) is the correct approach. Adding `source_tier: str = "full"` to `ExtractedContent` costs 1 line (frozen dataclass with default = backward compatible). The cascade already knows which content is a snippet at creation time (`_snippet_fallback()`). Threading through `summarize_content()` → `summarize_chunk()` → `Summary` follows the same pattern as `url` and `title`. This avoids text-prefix detection entirely.

The YAGNI concern from the brainstorm (adding to `ExtractedContent` is "more architecturally complete but over-builds") is mitigated: we need to set the field *somewhere*, and the cascade is the point of knowledge. Detecting from text prefix in `summarize_content()` would be the fragile option the brainstorm explicitly rejected.

---

## Session 1: Raise Relevance Cutoff + A/B Test

### What exactly is changing?

**File: `research_agent/modes.py`** — Change `relevance_cutoff` in `standard()` and `deep()` factory methods:

```python
# standard() — line 140
relevance_cutoff=4,  # was 3

# deep() — line 166
relevance_cutoff=4,  # was 3
```

Quick mode stays at `relevance_cutoff=3` (line 112). No other code changes — `evaluate_sources()` in `relevance.py` already reads `mode.relevance_cutoff` dynamically.

### What must NOT change?

- `score_source()` prompt and scoring logic — unchanged
- Quick mode's `relevance_cutoff=3` — unchanged
- Gate decision logic in `evaluate_sources()` — unchanged (reads from mode)
- All existing tests that use `relevance_cutoff=3` — still valid for quick mode tests

### How will we know it worked?

**A/B test (quick manual check):**

Run 10 queries in standard mode, comparing gate decisions at cutoff=3 vs cutoff=4:

| Query type | Example | Expected |
|-----------|---------|----------|
| Specific technical | "Python asyncio semaphore patterns" | No flip (good sources score 4-5) |
| Specific factual | "SpaceX Starship launch dates 2026" | No flip |
| Broad technical | "machine learning trends" | Possible flip — investigate |
| Niche topic | "post-quantum cryptography standards" | Possible flip |
| Current events | "recent AI regulation EU" | No flip |
| Comparison | "React vs Vue 2026" | No flip |
| Local/specific | "best coffee shops Portland Oregon" | Possible flip |
| How-to | "how to deploy FastAPI on AWS Lambda" | No flip |
| Industry | "renewable energy market growth" | No flip |
| Emerging tech | "WebAssembly server-side use cases" | Possible flip |

**Decision rule:** If any query flips from `full_report` to `short_report` or worse, investigate whether the lost sources scored exactly 3 and whether they were genuinely useful. If a mainstream query (not a niche edge case) loses useful sources, reconsider.

**Method:** Temporarily set cutoff=3 (current), run query, note decision. Then set cutoff=4, run same query, note decision. Compare. No env var needed — just edit the factory method, run, and check.

**Unit tests:**
- `test_modes.py`: Verify `ResearchMode.standard().relevance_cutoff == 4`
- `test_modes.py`: Verify `ResearchMode.deep().relevance_cutoff == 4`
- `test_modes.py`: Verify `ResearchMode.quick().relevance_cutoff == 3`
- Existing relevance tests still pass (they construct modes directly or use quick mode)

### Research Insights (Session 1)

**Haiku borderline interaction (from Cycle 21 solution doc — `tiered-model-routing-planning-vs-synthesis.md`):**
Relevance scoring uses Haiku (`mode.relevance_model`). Cycle 21 noted Haiku scores borderline sources more aggressively than Sonnet (zoning query: 12→7 sources). At cutoff=3, this didn't flip decisions. At cutoff=4, sources scoring exactly 3 under Haiku (that Sonnet might score 4) are now excluded. The A/B test should note any queries where source counts drop significantly — this may indicate Haiku borderline aggressiveness compounding with the higher cutoff.

**Pre-test sanity check (from Cycle 21 lesson — "clean the measurement instrument before measuring"):**
Before the A/B comparison, verify `score_source()` produces expected scores on 2-3 known-quality sources. If scores are surprising, investigate before attributing differences to the cutoff.

**Additional A/B test queries (from spec-flow analysis):**
Add 3 high-risk query types to the test table:
| Aggregator-heavy | "best project management tools 2026" | Possible flip — Haiku scores aggregators low |
| Person-specific | "John Smith CEO XYZ Corp" | Possible flip — thin results |
| Very recent events | "latest AI model releases April 2026" | Possible flip — sources may be thin |

### Most likely way this plan is wrong?

The A/B test reveals that raising from 3 to 4 drops useful sources on niche or broad queries. Mitigation: the test explicitly checks these categories. If flips occur, the fix is a 1-line revert per mode. **Secondary risk:** Haiku borderline aggressiveness compounds with the higher cutoff, causing more aggressive source exclusion than the cutoff change alone would explain.

### Exact steps

1. Edit `modes.py`: Change `relevance_cutoff=4` in `standard()` and `deep()`.
2. Run `python3 -m pytest tests/test_modes.py -v`.
3. Pre-test sanity check: verify score_source() on 2-3 known sources.
4. Run A/B test: 13 queries at cutoff=3 vs cutoff=4 (see table above + 3 high-risk additions).
4. Document A/B results in commit message.
5. Add unit tests for the new cutoff values.
6. Run full suite: `.venv/bin/python -m pytest tests/ --ignore=tests/test_mcp_server.py -q`.
7. Commit: `feat(28-1): raise relevance cutoff to 4 for standard/deep modes`

---

## Session 2: Snippet Quality Tier

### What exactly is changing?

**File: `research_agent/extract.py`** — Add type alias and 1 field to `ExtractedContent`:

```python
from typing import Literal

SourceTier = Literal["full", "snippet"]

@dataclass(frozen=True)
class ExtractedContent:
    """Extracted content from a web page."""
    url: str
    title: str
    text: str
    source_tier: SourceTier = "full"
```

**File: `research_agent/cascade.py`** — Set `source_tier="snippet"` in `_snippet_fallback()`:

```python
# Line 245 — add source_tier kwarg
ExtractedContent(
    url=r.url,
    title=r.title,
    text=f"[Source: search snippet] {r.snippet}",
    source_tier="snippet",
)
```

**File: `research_agent/summarize.py`** — Add `source_tier` to `Summary` and thread through:

```python
from .extract import SourceTier

@dataclass(frozen=True)
class Summary:
    """A summary of a content chunk."""
    url: str
    title: str
    summary: str
    source_tier: SourceTier = "full"
```

In `summarize_chunk()` (line 71): add `source_tier: SourceTier = "full"` parameter, pass to `Summary()` constructor at line 145.

In `summarize_content()` (line 158): pass `content.source_tier` to `summarize_chunk()` calls at lines 188-196.

**File: `research_agent/relevance.py`** — Add named constant and cap snippet scores in `score_source()`:

At module level:
```python
SNIPPET_SCORE_CAP: int = 3  # Snippets are thin content — cap regardless of LLM score
```

**Immediately before the `return SourceScore(...)` statement** (covers ALL exit paths — happy parse, empty response, rate limit, API error):

```python
# Cap snippet scores — thin content shouldn't score above SNIPPET_SCORE_CAP
if summary.source_tier == "snippet" and score > SNIPPET_SCORE_CAP:
    logger.info("Capping snippet score from %d to %d for %s", score, SNIPPET_SCORE_CAP, summary.url)
    score = SNIPPET_SCORE_CAP
```

**Important:** The cap MUST be placed after all branches that assign a score (happy path at ~line 179, error defaults at ~lines 176/182/184), not just after the happy-path parse. This ensures the cap is robust to future changes in default score values.

**No changes to `agent.py`** — it calls `summarize_all()` which receives `ExtractedContent` objects (already have tier). It calls `evaluate_sources()` which receives `Summary` objects (now have tier). The tier flows through the existing pipeline.

### Call-site audit

**`ExtractedContent(` constructors — 6 production sites:**

| File:Line | Sets `source_tier`? | Why |
|-----------|-------------------|-----|
| `extract.py:76` | No (default "full") | trafilatura extraction — full content |
| `extract.py:103` | No (default "full") | readability fallback — full content |
| `cascade.py:179` | No (default "full") | Jina Reader — full content |
| `cascade.py:209` | No (default "full") | Tavily Extract — full content |
| `cascade.py:245` | Yes → "snippet" | Snippet fallback — the only snippet source |
| `agent.py:539` | No (default "full") | Prefetched content — full content |

All 104 test `ExtractedContent(` constructors use positional/keyword args without `source_tier` → get default "full". No test changes needed.

**`Summary(` constructors — 1 production site:**

| File:Line | Threads `source_tier`? | Why |
|-----------|----------------------|-----|
| `summarize.py:145` | Yes → from parameter | Only production constructor |

All 104 test `Summary(` constructors use `url, title, summary` without `source_tier` → get default "full". No test changes needed for existing tests.

### What must NOT change?

- Full-content sources must still score 1-5 without capping
- Snippet text prefix `[Source: search snippet]` stays as-is (for human readability)
- `summarize_chunk()` prompt and behavior unchanged
- `score_source()` prompt and LLM scoring unchanged — only the post-parse cap is new
- Source aggregation logic (`_aggregate_by_source`) unchanged — uses max score per URL, which now uses capped scores
- **Score cap invariant (from Cycle 22 solution — "short-circuits must preserve invariants"):** Verify no production code path feeds `Summary` objects into `evaluate_sources()` without going through `score_source()`. If one exists, the cap would be bypassed.
- **Interaction with Session 1 cutoff raise:** A snippet-only source will have all chunks capped at 3. After aggregation (max per URL), the source scores 3. At the new standard/deep cutoff of 4, snippet-only sources are always excluded. At quick mode cutoff of 3, they survive. This is the intended layered behavior.
- **Coverage gap retry path:** Verify that `_try_coverage_retry` in agent.py uses the same cascade/summarize pipeline (so `source_tier` is threaded correctly for retry results too)

### How will we know it worked?

1. **Unit test: `ExtractedContent` has `source_tier` field:**
   - `ExtractedContent(url="u", title="t", text="x").source_tier == "full"`
   - `ExtractedContent(url="u", title="t", text="x", source_tier="snippet").source_tier == "snippet"`

2. **Unit test: `Summary` has `source_tier` field:**
   - Same pattern as above.

3. **Unit test: Score capping in `score_source()`:**
   - Mock LLM returns score 5 for a snippet summary → final score is 3
   - Mock LLM returns score 3 for a snippet summary → final score stays 3
   - Mock LLM returns score 2 for a snippet summary → final score stays 2
   - Full summary scoring unchanged regardless of score

4. **Integration test: Snippet excluded from standard mode:**
   - Create a mock scenario: 3 full sources (score 4) + 1 snippet (LLM score 4, capped to 3)
   - Standard mode (cutoff=4): snippet dropped, 3 full sources survive
   - Quick mode (cutoff=3): snippet survives with all 4

5. **Existing test suite passes unchanged** (defaults protect all constructors).

### Most likely way this plan is wrong?

The score cap is applied in `score_source()` which scores individual chunks, not aggregated sources. `_aggregate_by_source()` takes the max score per URL. If a URL has both snippet and full-content chunks (unlikely but possible in theory), the max score would be the uncapped full-content score. This is actually correct behavior — if we have full content from a URL, the snippet is redundant and the full score should win.

### Exact steps

1. Add `SourceTier = Literal["full", "snippet"]` type alias and `source_tier: SourceTier = "full"` to `ExtractedContent` in `extract.py`.
2. Set `source_tier="snippet"` in `_snippet_fallback()` in `cascade.py`.
3. Import `SourceTier` and add `source_tier: SourceTier = "full"` to `Summary` in `summarize.py`.
4. Add `source_tier: str = "full"` to `summarize_chunk()` signature, pass to `Summary()`.
5. Pass `content.source_tier` from `summarize_content()` to `summarize_chunk()`.
6. Add `SNIPPET_SCORE_CAP = 3` constant and score cap in `score_source()` in `relevance.py` — place before `return SourceScore(...)` to cover all exit paths.
7. Write unit tests for new fields and score capping.
8. Write integration test for snippet exclusion at different cutoffs.
9. Run `.venv/bin/python -m pytest tests/ --ignore=tests/test_mcp_server.py -q`.
10. Commit: `feat(28-2): add snippet quality tier with score cap at 3`

---

## Session 3: Quick Mode Min Sources

### What exactly is changing?

**File: `research_agent/modes.py`** — Change `min_sources_short_report` in `quick()`:

```python
# quick() — line 111
min_sources_short_report=2,  # was 1
```

No other code changes needed. The gate logic in `evaluate_sources()` already handles the threshold:

```python
# relevance.py:338 — existing logic
elif total_survived >= mode.min_sources_short_report:
    decision = "short_report"
```

With `min_sources_short_report=2`, a quick-mode query with 1 surviving source falls through to the `insufficient_data` branch (line 351), which already generates a response mentioning the query and dropped sources.

**File: `research_agent/relevance.py`** — Add `surviving_sources` parameter to `generate_insufficient_data_response()`.

Currently (line 383+), the function receives `dropped_sources` but NOT surviving sources. Confirmed by repo research: neither the LLM prompt path nor the fallback path surfaces surviving source URLs. When quick mode has 1 surviving source, the user is told "insufficient data" with no mention of the relevant source.

**Required change:** Add `surviving_sources: tuple[Summary, ...] = ()` parameter. When non-empty, append a line to the response: "However, one relevant source was found: [title] ([url]) — you may want to investigate it directly."

**File: `research_agent/agent.py`** — Update the call site at line ~840 to pass `surviving_sources=evaluation.surviving_sources` when the decision is `insufficient_data`.

### What must NOT change?

- Standard and deep mode `min_sources_short_report` values (2 and 5) — unchanged
- Gate decision logic structure — unchanged
- `insufficient_data` response generation — function signature gains an optional `surviving_sources` parameter (backward compatible)

### How will we know it worked?

1. **Unit test:** `ResearchMode.quick().min_sources_short_report == 2`
2. **Gate decision test:** Mock scenario with 1 surviving source in quick mode → decision is `insufficient_data` (not `short_report`)
3. **Gate decision test:** Mock scenario with 2 surviving sources in quick mode → decision is `short_report` (still works)
4. **Gate decision test:** Mock scenario with 0 surviving sources → decision is `insufficient_data` or `no_new_findings` (unchanged)
5. **Verify insufficient_data response mentions the surviving source URL** (if applicable)

### Most likely way this plan is wrong?

The `insufficient_data` response path may not mention the surviving source. Currently `generate_insufficient_data_response()` only receives `dropped_sources`. If 1 source survived but below the new threshold, that source isn't "dropped" — it passed relevance but the count is too low. The response should mention it. This may require passing surviving sources to the response generator, or adjusting the prompt to mention them.

Repo research confirmed: the current response surfaces dropped source titles/scores but NOT URLs, and does NOT mention surviving sources. This is a required change — the brainstorm explicitly promises "user gets the URL to investigate."

### Exact steps

1. Change `min_sources_short_report=2` in `quick()` factory method.
2. Add `surviving_sources: tuple[Summary, ...] = ()` parameter to `generate_insufficient_data_response()` in `relevance.py`.
3. Update the LLM prompt and fallback path to mention surviving source URLs when non-empty.
4. Update `agent.py` call site (~line 840) to pass `surviving_sources=evaluation.surviving_sources`.
4. Write unit tests for new threshold value.
5. Write gate decision tests for 0, 1, and 2 surviving sources in quick mode.
6. Run `.venv/bin/python -m pytest tests/ --ignore=tests/test_mcp_server.py -q`.
7. Commit: `feat(28-3): raise quick mode min sources to 2`

---

## Plan Quality Gate

| Question | Answer |
|----------|--------|
| What exactly is changing? | 3 items: `relevance_cutoff` raised to 4 in standard/deep (1 line each), `source_tier` field on `ExtractedContent` + `Summary` with score cap in `score_source()` (~25 lines across 4 files), `min_sources_short_report` raised to 2 for quick mode (1 line + possible response adjustment) |
| What must NOT change? | Score prompts and LLM scoring behavior. Quick mode's cutoff=3. Gate decision logic structure. All existing tests (defaults protect constructors). Source aggregation (max per URL). |
| How will we know it worked? | A/B test shows no decision flips on mainstream queries. Snippet scores capped at 3 (verified by mock). Quick mode requires 2+ sources (gate test). Full test suite passes. |
| Most likely way this plan is wrong? | (1) A/B test reveals cutoff=4 drops useful sources on niche queries — mitigation: 1-line revert. (2) `generate_insufficient_data_response` doesn't mention the 1 surviving source URL — mitigation: small prompt adjustment or accept as-is. |

---

## Feed-Forward

- **Hardest decision:** Resolving the brainstorm's "least confident" item — whether to add `source_tier` to `ExtractedContent` or detect text prefixes. Chose `ExtractedContent` because the cascade is the point of knowledge. The YAGNI trade-off (brainstorm preferred Summary-only) was overridden because text-prefix detection would reintroduce the exact fragility the brainstorm rejected.

- **Rejected alternatives:** (1) Adding `source_tier` only to `Summary` without `ExtractedContent` — would require detecting the `[Source: search snippet]` text prefix in `summarize_content()`, which is the fragile approach the brainstorm rejected. (2) Using bare `str` for `source_tier` — `Literal["full", "snippet"]` catches typos at type-check time with zero runtime cost. (3) Making snippet score cap a `ResearchMode` field — the cap is a property of snippet quality, not research mode; different modes capping snippets at different values would be confusing.

- **Least confident:** The A/B test outcome. If raising cutoff to 4 causes significant decision flips on mainstream queries (not niche edge cases), we may need to keep cutoff=3 for standard and only raise for deep. The test table covers 10 diverse query types to surface this early. The mitigation is a 1-line revert — low cost if the test fails.
