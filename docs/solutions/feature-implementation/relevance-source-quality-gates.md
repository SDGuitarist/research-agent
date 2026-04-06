---
cycle: 28
title: "Relevance & Source Quality Gates"
date: 2026-04-05
modules: [relevance, modes, extract, cascade, summarize, agent, results, mcp_server]
tags: [relevance-scoring, source-quality, snippet-tier, cutoff, MCP-parity, entropy-roadmap]
commits: ["16e0a0b", "7273f25", "81e8c33", "93d81cb", "dd790ce"]
plan: "docs/plans/2026-04-05-cycle-28-relevance-source-quality-plan.md"
brainstorm: "docs/brainstorms/2026-04-05-cycle-28-relevance-cutoff-brainstorm.md"
---

# Relevance & Source Quality Gates

## Problem

Three entropy/quality issues from the entropy audit roadmap (cycles 27-31):

1. **Low-quality sources passing the relevance gate.** Standard and deep modes used `relevance_cutoff=3`, allowing "partially relevant" sources into reports. These diluted quality without adding substance.

2. **Snippet sources scoring as high as full-content sources.** Cascade fallback produced search snippets (50-200 chars) that the LLM scored 4-5 based on topical relevance, ignoring content depth. A snippet about the right topic scored identically to a 2000-word article.

3. **Single-source quick-mode reports.** `min_sources_short_report=1` allowed reports from a single source with no cross-source validation.

## Root Cause

The pipeline was designed for availability before quality:

- `relevance_cutoff=3` was conservative from Cycle 15 when source counts were lower.
- `ExtractedContent` and `Summary` had no content quality tier. Snippet fallbacks were structurally identical to full extractions -- the only marker was a `[Source: search snippet]` text prefix the scoring LLM ignored.
- Quick mode's threshold was set to 1 for maximum availability.

## Solution

### Change 1: Raise relevance cutoff (2 lines in modes.py)

```python
# standard() and deep() factory methods
relevance_cutoff=4,  # was 3
```

Quick mode stays at `relevance_cutoff=3`. No logic changes -- `evaluate_sources()` reads `mode.relevance_cutoff` dynamically.

### Change 2: Snippet quality tier (~25 lines across 4 files)

Added `SourceTier = Literal["full", "snippet"]` in `extract.py`. Threaded through:

- `ExtractedContent.source_tier` (default `"full"`)
- `cascade._snippet_fallback()` sets `source_tier="snippet"` at creation time
- `summarize_chunk()` / `summarize_content()` thread to `Summary.source_tier`
- `score_source()` applies cap before returning:

```python
SNIPPET_SCORE_CAP: int = 3

# Immediately before return SourceScore(...) — covers all exit paths
if summary.source_tier == "snippet" and score > SNIPPET_SCORE_CAP:
    score = SNIPPET_SCORE_CAP
```

**Layered interaction:** At cutoff=4, snippets (capped at 3) are always excluded in standard/deep. At cutoff=3 (quick), they survive. Intentional.

### Change 3: Quick mode min sources + surviving source surfacing

```python
# modes.py quick()
min_sources_short_report=2,  # was 1
```

`generate_insufficient_data_response()` gained `surviving_sources: tuple[Summary, ...] = ()`. When 1 source survives but falls below threshold, the response surfaces the URL. Both LLM and fallback paths handle it.

## Key Decisions

### source_tier on ExtractedContent vs Summary-only

The brainstorm preferred Summary-only (YAGNI). The plan overrode: the cascade is the point of knowledge -- it knows at creation time whether content is a snippet. Detecting the text prefix in `summarize_content()` would be fragile (the exact approach the brainstorm rejected). Adding `source_tier` to `ExtractedContent` costs 1 line with a default value -- zero backward compatibility impact across 39 test constructors.

### Score cap placement

Placed immediately before `return SourceScore(...)` -- after ALL four score-assignment branches (happy parse, empty response, RateLimitError, APIError). Unhandled exceptions propagate without returning a SourceScore, so the cap doesn't need to cover those. Identified during plan deepening.

### Surviving sources in XML boundaries

Initial implementation put surviving sources outside XML tags in the LLM prompt. Review caught this as a defense-in-depth gap -- `<dropped_sources>` had XML boundaries but surviving sources didn't. Fixed by wrapping in `<surviving_sources>` tags.

## Review Findings

7-agent review: 0 P1, 3 P2, 5 P3. All P2s fixed in commit `dd790ce`:

| # | Finding | Fix |
|---|---------|-----|
| 1 | `chr(10)` trick in f-string unreadable | Extracted `_build_instruction_list()` helper |
| 2 | ModeInfo missing relevance gate fields (MCP parity) | Added `relevance_cutoff`, `min_sources_full_report`, `min_sources_short_report` to ModeInfo + list_research_modes |
| 3 | Surviving sources lack XML boundary | Wrapped in `<surviving_sources>` tags |

**Known pattern:** MCP parity gaps are the most common review finding (also flagged in Cycles 19, 26, 27). When adding mode fields, always update `ModeInfo` in `results.py`, `list_modes()` in `__init__.py`, and `list_research_modes` in `mcp_server.py` in the same commit.

## Risk Resolution

**Feed-Forward risk from plan:** "A/B test outcome -- cutoff=4 may compound with Haiku borderline aggressiveness."

**What actually happened:** Live A/B testing was blocked by expired API key. Code analysis using Cycle 21 scoring data (9 queries) supports the raise -- Haiku produces clean 1/4/5 distributions, score-3 sources are genuinely borderline. A validation script (`scripts/validate_cutoff_ab.py`) is ready to run when keys are renewed. Mitigation: 1-line revert per mode.

**Lesson:** Validation scripts should test API connectivity before running the full suite. The expired key produced 0 results with no clear error until output inspection.

## Prevention & Future Guidance

1. **When adding frozen dataclass fields:** Use defaults for backward compatibility. Audit constructors in tests (Cycle 28: 39 ExtractedContent + 104 Summary sites, all safe via defaults).

2. **When changing relevance thresholds:** Score once, replay gate logic at multiple cutoffs. Don't re-score -- it wastes API credits and introduces variability.

3. **When adding content to LLM prompts:** Wrap in XML boundary tags (`<tag>content</tag>`). Defense-in-depth requires all three layers: sanitize + XML boundaries + system prompt.

4. **MCP parity checklist (from Cycle 19):** Every `ResearchMode` field change needs corresponding `ModeInfo` field + `list_research_modes` output + `instructions` string review.

## Related Docs

| Doc | Relationship |
|-----|-------------|
| [source-level-relevance-aggregation](../logic-errors/source-level-relevance-aggregation.md) (C15) | **Extended** -- cutoff/gate changes build on per-source aggregation |
| [tiered-model-routing](../architecture/tiered-model-routing-planning-vs-synthesis.md) (C21) | **Complemented** -- Haiku scoring data informed A/B analysis |
| [input-validation-and-generation-controls](input-validation-and-generation-controls.md) (C27) | **Complemented** -- immediate predecessor on entropy roadmap |
| [mcp-server-boundary-protection](../security/mcp-server-boundary-protection-and-agent-parity.md) (C19) | **Complied with** -- parity checklist followed |
| [mcp-parity-lint-ci-enforcement](../workflow/mcp-parity-lint-ci-enforcement.md) (C26) | **Complemented** -- CI lint validates new MCP changes |

## Three Questions

1. **Hardest pattern to extract from the fixes?** The layered interaction between snippet cap (3), quick cutoff (3), and standard/deep cutoff (4). It produces clear behavior but requires understanding all three values together. Documented as "intentional layered behavior" with dedicated interaction tests.

2. **What did you consider documenting but left out?** The `_aggregate_by_source` exception-path score cap bypass (security review P2, downgraded to P3). Currently a no-op because exception default score (3) equals SNIPPET_SCORE_CAP (3). Worth fixing if the cap is ever lowered, but not worth a separate solution doc.

3. **What might future sessions miss that this solution doesn't cover?** The A/B live validation. Code analysis and historical data support the cutoff raise, but no live Haiku scores at cutoff=4 have been observed. If production queries show unexpected `insufficient_data` results in standard mode, the first thing to check is whether sources are clustering at score 3.
