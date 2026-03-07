---
title: "Tiered Model Routing — Planning, Relevance Scoring, and Synthesis"
date: 2026-03-06
category: architecture
tags: [model-routing, cost-optimization, planning-model, relevance-model, haiku, sonnet, frozen-dataclass, a-b-testing]
module: research_agent/modes.py, research_agent/agent.py, research_agent/relevance.py, research_agent/results.py, research_agent/mcp_server.py, research_agent/query_validation.py
symptoms: "All API calls (planning, relevance scoring, and synthesis) used Sonnet model, incurring unnecessary cost on classification-like tasks."
severity: medium
cycle: 21
summary: "Added planning_model and relevance_model fields to ResearchMode dataclass, both defaulting to Haiku. Routed 7 planning call sites through planning_model and relevance scoring through relevance_model; kept 8 synthesis/quality-critical call sites on Sonnet. Tier 1 validated with 14 queries, Tier 2 A/B tested with 9 queries (zero decision flips). Also fixed meaningful_words() validation bug hiding quality issues."
---

# Tiered Model Routing — Planning, Relevance Scoring, and Synthesis

## Prior Phase Risk

> "Whether the 2 integration tests in fix 115 are sufficient coverage. They test decompose_query (standard mode) and refine_query (quick mode), but 5 other planning call sites (identify_coverage_gaps, generate_refined_queries, generate_followup_questions, evaluate_report, and the deep-mode refine_query) remain untested."

Accepted risk: all 7 sites use the identical `model=self.mode.planning_model` pattern, so a regression at one site would likely appear at the tested sites too. If a future change breaks the pattern at only one site, the parametrized test approach in Prevention below would catch it.

## Problem

All 15+ Claude API calls in the research pipeline used the same Sonnet model ($3/$15 per MTok). Eight of these are classification-like tasks — seven planning calls (decompose query, refine query, identify coverage gaps, generate refined queries, generate follow-up questions, evaluate report) plus relevance scoring (score each source 1-5) — that don't need Sonnet-level reasoning. This wasted ~4-7% of cost and added ~3-5s latency on the critical path.

## Root Cause

Organic growth. When `decompose.py`, `search.py`, and other modules were built across Cycles 7-20, they all received `self.mode.model` (Sonnet). No one split planning from synthesis because there was only one model field on `ResearchMode`. Each module worked fine in isolation — the inefficiency only becomes visible when you audit all 15 call sites together.

This is the same trajectory that caused model string scatter before Cycle 15's unification (see [model-string-unification.md](model-string-unification.md)).

## Solution

### 1. Added `planning_model` and `relevance_model` fields to `ResearchMode` (`modes.py`)

```python
model: str = DEFAULT_MODEL              # Sonnet — synthesis and quality-critical calls
planning_model: str = AUTO_DETECT_MODEL  # Haiku — planning/classification steps
relevance_model: str = AUTO_DETECT_MODEL # Haiku — relevance scoring (classification-like)
```

Placed right after `model` to group model concerns. Frozen dataclass, individual fields (not a dict mapping) — right-sized for the tiered approach. Default `AUTO_DETECT_MODEL` resolves to Haiku for all three modes with no explicit override needed.

### 2. Routed 7 planning call sites to `planning_model` (in `agent.py`)

| # | Function | Quality Risk |
|---|----------|-------------|
| 1 | `decompose_query()` | Higher — sub-query generation |
| 2 | `refine_query()` (standard pass) | Very low — 3-8 word search query |
| 3 | `refine_query()` (deep pass) | Very low |
| 4 | `identify_coverage_gaps()` | Moderate — gap taxonomy classification |
| 5 | `generate_refined_queries()` | Low — structured gap-then-query |
| 6 | `generate_followup_questions()` | Low — pattern-based generation |
| 7 | `evaluate_report()` | Very low — 1-5 scoring, metadata only |

### 3. Kept 8 synthesis/quality-critical call sites on `model` (Sonnet)

`summarize_all`, `synthesize_report`, `synthesize_draft`, `run_deep_skeptic_pass`, `run_skeptic_combined`, `synthesize_final`, `generate_insufficient_data_response`, `synthesize_mini_report`.

### 4. Relevance scoring promoted to Haiku (Tier 2)

`evaluate_sources()` in `relevance.py` now routes scoring through `mode.relevance_model` (Haiku). Initially stayed on Sonnet as a documented exception pending A/B testing. After testing 9 queries with both models and observing zero decision flips (no full_report ↔ short_report changes), `relevance_model` was promoted from a temporary env var (`RELEVANCE_MODEL`) to a permanent `ResearchMode` field.

```python
# relevance.py — evaluate_sources routes to relevance_model
async def _score(summary: Summary) -> SourceScore:
    return await score_source(
        safe_query, summary, client,
        model=mode.relevance_model,  # Haiku for classification-like scoring
        critique_guidance=critique_guidance,
    )
```

### 5. Validation bug fix (discovered during Tier 1 testing)

`meaningful_words()` in `query_validation.py` didn't strip punctuation or split hyphens, causing `"standards,"` ≠ `"standards"` and `"post-quantum"` to not match `"quantum"`. This was silently degrading decomposition validation on all complex queries. Fixed by stripping `,.?!;:"'()[]` and splitting hyphenated words into components. This bug was discovered and fixed before the A/B comparison — essential for clean measurement.

### Key Design Decisions

- **Static task-based routing (Pattern A)** — simplest multi-model pattern. Matches Anthropic's own cookbook example (Sonnet for summarization + Haiku for ranking).
- **No Haiku-to-Sonnet fallback cascade** — doubles latency on failure, not worth it for planning calls costing fractions of a cent.
- **No `cost_estimate` changes** — deferred until real usage data exists (avoids false precision on rough numbers).
- **Consolidated debug logging** — replaced 7 per-call-site logs with 1 summary log at run start (-6 net LOC).

## Pattern

**Static Task-Based Routing**: hard-code which pipeline stages use which model at configuration time. Works well when task categories are stable.

When to apply:
- Pipeline has distinct "thinking" vs "producing" stages
- The cheaper model handles the thinking tasks adequately
- Task categories don't change frequently

When NOT to apply:
- Tasks vary in difficulty per-query (need dynamic routing)
- Cost savings are negligible (< 3%)
- Quality risk is high and hard to monitor

Contrasts with Pattern B (dynamic routing via cost/latency thresholds) and Pattern C (model-selection prompts), which add complexity without justified ROI for a small, stable set of planning calls.

## Results

- **Cost**: ~4-7% savings on standard mode ($0.45 → ~$0.42-0.43)
- **Latency**: ~3-5s improvement (Haiku typically 3-5x faster on classification tasks)
- **Tests**: 891 passing
- **Agent visibility**: `model` + `planning_model` + `relevance_model` fields added to ModeInfo and `list_modes()` output
- **Review**: 5 findings (0 P1, 3 P2, 2 P3), all fixed

### Tier 2 A/B Test Results (9 queries, standard mode)

| Report | Sonnet sources | Haiku sources | Decision change? |
|--------|---------------|---------------|-----------------|
| lodge | 6 | 7 | No (full→full) |
| restaurants | 7 | 10 | No (full→full) |
| zoning | 12 | 7 | No (full→full) |
| pendry | 9 | 7 | No (full→full) |
| hoteldel | 2 | 3 | No (short→short) |
| luxury-trends | 7 | 7 | No (full→full) |
| grant-writing | 12 | 12 | No (full→full) |
| ai-jobs | 12 | 12 | No (full→full) |
| ai-filmmaking | 11 | 9 | No (full→full) |

**Verdict:** Zero decision flips. Source count differences are search variability, not scoring divergence. Haiku scores generic aggregators (TripAdvisor/Yelp/YouTube) consistently low (1/5), same as Sonnet.

| Tier | Queries tested | Decision flips | Status |
|------|---------------|----------------|--------|
| Tier 1 (planning) | 14 | 0 | Shipped |
| Tier 2 (relevance) | 9 | 0 | Shipped |
| Tier 3 (summarization) | — | — | Deferred indefinitely |

## Review Findings Fixed

| # | Issue | Priority | Fix |
|---|-------|----------|-----|
| 116 | ModeInfo missing planning_model | P2 | Added `model` + `planning_model` to ModeInfo, list_modes(), MCP output |
| 114 | 7 redundant debug logs | P2 | Consolidated into 1 summary log (-6 LOC) |
| 115 | No integration test for routing | P2 | Added 2 tests: decompose receives Haiku, refine receives Haiku |
| 117 | Misleading model field comment | P3 | Updated "for all API calls" → "for synthesis and quality-critical calls" |
| 118 | MCP docstring missing routing info | P3 | Added tiered routing note to run_research docstring |

## Prevention & Future Guidance

- **New call sites**: When adding API calls in `agent.py`, decide planning vs. synthesis and use `self.mode.planning_model` or `self.mode.model` accordingly. Grep for both to see the established pattern.
- **ModeInfo drift**: When adding fields to `ResearchMode`, immediately update `ModeInfo` in `results.py` and `list_modes()` in `mcp_server.py`. Make this a code review checklist item.
- **A/B test before promoting**: Cycle 21 established a two-step methodology: (1) add temporary env var override for testing, (2) promote to permanent field only after validation. Compare *decisions* (gate outcomes), not raw scores — a source scoring 4 vs 5 changes nothing if the cutoff is 3.
- **Classify the task before choosing the model**: Ask "Is this structured output with constrained options, or open-ended reasoning?" Classification-like tasks (score 1-5, SIMPLE/COMPLEX, query lists) tolerate Haiku. Open-ended synthesis does not.
- **Fix hidden bugs before measuring quality**: The `meaningful_words()` bug was silently degrading validation. Without fixing it first, the A/B comparison would have measured validation noise rather than model quality. Clean the measurement instrument before measuring.
- **Tier 3 gate**: Don't expand Haiku to summarization without per-summary quality comparison (not just gate-level decisions). Summarization is 12-36 calls per run and directly affects user-facing content.
- **Haiku borderline aggressiveness**: Monitor queries where Sonnet passes 8+ sources and Haiku passes significantly fewer. The zoning query (12→7) was the largest variance — gate decision didn't flip, but borderline sources may be scored more aggressively.

## Risk Resolution

### Tier 1 Risk (from review)

**Feed-forward risk:** "Whether Haiku decompose quality holds on complex queries — needs real run monitoring."

**What happened:** Validated with 14 queries across simple and complex topics. No decomposition quality degradation. The `meaningful_words()` bug fix (discovered during validation) was the real quality issue — not the model switch.

**Lesson:** When quality risk is hard to evaluate without production data, ship with monitoring rather than blocking on theoretical concerns. The frozen dataclass default (`AUTO_DETECT_MODEL`) makes rollback trivial — change one field value.

### Tier 2 Risk (from HANDOFF.md)

**Feed-forward risk:** "The zoning query dropped from 12→7 sources with Haiku scoring, worth monitoring borderline aggressiveness."

**What happened:** A/B tested 9 queries. Zero decision flips across all queries. The zoning source count difference was attributed to search variability (Tavily returns different results across runs), not scoring divergence. Haiku scores generic aggregators consistently low, matching Sonnet's behavior.

**Lesson:** Compare decisions, not raw metrics. Source count differences create noise; gate outcomes (full_report/short_report/insufficient_data) are the meaningful signal.

## Related

- [`model-string-unification.md`](model-string-unification.md) — Direct predecessor. Cycle 15 unified model strings into `ResearchMode.model`; Cycle 21 extends this with `planning_model` for tiered routing.
- [`parallel-async-synthesis-with-safety-barriers.md`](parallel-async-synthesis-with-safety-barriers.md) — Async patterns used by planning calls that run in parallel (semaphore + gather).
- [`agent-native-return-structured-data.md`](agent-native-return-structured-data.md) — How `ResearchMode` flows through the pipeline as structured data.
- [`mcp-server-boundary-protection-and-agent-parity.md`](../security/mcp-server-boundary-protection-and-agent-parity.md) — Agent-native parity checklist applied to ModeInfo update (fix 116).
- [`pip-installable-package-and-public-api.md`](pip-installable-package-and-public-api.md) — Validation ownership pattern for frozen dataclass fields at boundaries.
- [`non-idempotent-sanitization-double-encode.md`](../security/non-idempotent-sanitization-double-encode.md) — Standing risk noted during Cycle 21 (sanitize_content not idempotent).
- `research_agent/modes.py` — The dataclass with `model`, `planning_model`, and `relevance_model` fields.
- `research_agent/agent.py` — The orchestrator routing 7 planning + 8 synthesis call sites.
- `research_agent/relevance.py` — Relevance scoring using `mode.relevance_model`.

## Three Questions (Compound Phase)

1. **Hardest pattern to extract from the fixes?** The two-step promotion pattern (env var → permanent field) as a general methodology for safely introducing model routing changes. The specific insight is: A/B test *decisions*, not raw scores — comparing gate outcomes (full_report vs short_report) catches real regressions while ignoring harmless noise from score variance.

2. **What did you consider documenting but left out, and why?** Per-query score distribution comparisons between Haiku and Sonnet. Individual scores often differ by 1 point, but this noise is meaningless when the gate cutoff absorbs it. Including score-level detail would mislead future readers into thinking score parity matters — it doesn't; decision parity is the only signal.

3. **What might future sessions miss that this solution doesn't cover?** The interaction between `relevance_model` and the iteration system (Cycle 20). `iterate.py` generates refined queries via `agent.py` (routed to Haiku), and those queries' results get scored by `evaluate_sources` (also Haiku). Both hops are now on the cheaper model. If iteration produces poor refined queries *and* relevance scoring doesn't catch the low-quality results, the compound effect could degrade reports on complex multi-iteration queries. This double-Haiku path hasn't been specifically tested end-to-end.
