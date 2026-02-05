# Relevance Scoring System

## Overview

The relevance gate evaluates source quality between summarization and synthesis, filtering out off-topic content before report generation.

```
Search → Fetch → Extract → Summarize → [RELEVANCE GATE] → Synthesize
```

## Scoring Rubric

Each source is scored 1-5 based on how well it addresses the original query:

| Score | Meaning | Action |
|-------|---------|--------|
| 5 | Directly answers the question with specific, on-topic information | KEEP |
| 4 | Strongly relevant with useful detail | KEEP |
| 3 | Partially relevant, touches on topic but missing key specifics | KEEP |
| 2 | Tangentially related, shares keywords but doesn't address the question | DROP |
| 1 | Off-topic, not useful | DROP |

Default cutoff: **score ≥ 3** (configurable via `relevance_cutoff` in ResearchMode)

## Mode Thresholds

| Mode | max_sources | min_sources_full_report | min_sources_short_report | Decision Logic |
|------|-------------|-------------------------|--------------------------|----------------|
| quick | 3 | 3 | 1 | All 3 must pass for full report |
| standard | 7 | 4 | 2 | 4+ for full, 2-3 for short |
| deep | 10 | 5 | 2 | 5+ for full, 2-4 for short |

## Decision Paths

### 1. `full_report`
- **Condition:** `surviving_sources >= min_sources_full_report`
- **Behavior:** Normal synthesis with all surviving sources
- **Output:** Complete research report

### 2. `short_report`
- **Condition:** `min_sources_short_report <= surviving_sources < min_sources_full_report`
- **Behavior:** Synthesis with disclaimer prepended
- **Output:** Shorter report with "limited information" warning

### 3. `insufficient_data`
- **Condition:** `surviving_sources < min_sources_short_report`
- **Behavior:** LLM generates explanation of what was searched and why it failed
- **Output:** Helpful "no data" response with alternative suggestions

## Async Parallel Scoring

Scoring uses `asyncio.gather()` for parallel execution:

```python
async def evaluate_sources(query, summaries, mode, client, refined_query=None):
    # Score all sources in parallel
    tasks = [score_source(query, summary, client) for summary in summaries]
    scored_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Partition into surviving/dropped based on cutoff
    for summary, result in zip(summaries, scored_results):
        if result["score"] >= mode.relevance_cutoff:
            surviving_sources.append(summary)
        else:
            dropped_sources.append(result)
```

Performance: With 7 sources, parallel scoring is ~7x faster than sequential.

## Implementation Files

- `research_agent/relevance.py` - Core scoring and evaluation logic
- `research_agent/modes.py` - Threshold configuration per mode
- `research_agent/agent.py` - Integration via `_evaluate_and_synthesize()` helper

## Error Handling

- API errors during scoring default to score 3 ("when in doubt, keep it")
- Empty responses default to score 3
- Exceptions from `gather()` are caught and logged, defaulting to score 3

---

## Threshold Observations

Findings from manual validation across multiple query types:

### What Worked Well

- **Thresholds worked out of the box** — no adjustments needed after implementation
- **Score 3 "when in doubt keep it" default proved correct** — API failures don't cause false drops
- **Standard mode's 7-source budget absorbs fetch failures gracefully** — even with 4/7 pages blocked, produces useful output

### Mode Fragility

- **Quick mode (3 sources) is fragile** — no buffer when fetches fail
  - Example: "guitarist pricing" query fetched 0/3 pages → total failure
  - Same query in standard mode fetched 3/7 → produced helpful insufficient_data response

### Gate Accuracy

- **Query 1 (noise ordinance):** Gate correctly caught flavor365.com food blog (score 1) that would have padded report with irrelevant content
- **Query 4 (rumba history):** Sources scored higher than expected (5/9 passed) — content was genuinely relevant to the comparative history question
- **Query 2 (guitarist pricing):** All sources scored 1-2, correctly triggering insufficient_data rather than a padded report

### Validation Summary

| Query | Sources | Passed | Decision | Gate Accuracy |
|-------|---------|--------|----------|---------------|
| Noise ordinance | 6 | 3 | short_report | Correct — dropped food blog |
| Guitarist pricing | 5 | 0 | insufficient_data | Correct — no pricing data |
| Wedding songs | 7 | 7 | full_report | Correct — all relevant |
| Rumba history | 9 | 5 | full_report | Correct — kept comparative sources |
| Hotel booking | 7 | 3 | short_report | Correct — dropped branding content |
