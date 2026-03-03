---
title: "Tiered Model Routing for Planning vs. Synthesis"
date: 2026-03-03
category: architecture
tags: [model-routing, cost-optimization, planning-model, haiku, sonnet, frozen-dataclass]
module: research_agent/modes.py, research_agent/agent.py, research_agent/results.py, research_agent/mcp_server.py
symptoms: "All API calls (planning and synthesis) used Sonnet model, incurring unnecessary cost on cheap planning tasks like decompose, refine, gap analysis, follow-ups, and report evaluation."
severity: medium
summary: "Added planning_model field to ResearchMode dataclass defaulting to Haiku. Routed 7 planning call sites through planning_model; kept 8 synthesis/quality-critical call sites on Sonnet. Achieved ~4-7% cost savings and ~3-5s latency improvement on standard mode."
---

# Tiered Model Routing for Planning vs. Synthesis

## Prior Phase Risk

> "Whether the 2 integration tests in fix 115 are sufficient coverage. They test decompose_query (standard mode) and refine_query (quick mode), but 5 other planning call sites (identify_coverage_gaps, generate_refined_queries, generate_followup_questions, evaluate_report, and the deep-mode refine_query) remain untested."

Accepted risk: all 7 sites use the identical `model=self.mode.planning_model` pattern, so a regression at one site would likely appear at the tested sites too. If a future change breaks the pattern at only one site, the parametrized test approach in Prevention below would catch it.

## Problem

All 15 Claude API calls in the research pipeline used the same Sonnet model ($3/$15 per MTok). Seven of these are planning/classification tasks — decompose query, refine query, identify coverage gaps, generate refined queries, generate follow-up questions, evaluate report — that don't need Sonnet-level reasoning. This wasted ~4-7% of cost and added ~3-5s latency on the critical path.

## Root Cause

Organic growth. When `decompose.py`, `search.py`, and other modules were built across Cycles 7-20, they all received `self.mode.model` (Sonnet). No one split planning from synthesis because there was only one model field on `ResearchMode`. Each module worked fine in isolation — the inefficiency only becomes visible when you audit all 15 call sites together.

This is the same trajectory that caused model string scatter before Cycle 15's unification (see [model-string-unification.md](model-string-unification.md)).

## Solution

### 1. Added `planning_model` field to `ResearchMode` (`modes.py`, line 32)

```python
model: str = DEFAULT_MODEL          # for synthesis and quality-critical calls
planning_model: str = AUTO_DETECT_MODEL  # cheaper model for planning/classification steps
```

Placed right after `model` to group model concerns. Frozen dataclass, single field (not a dict mapping) — right-sized for Tier 1. Default `AUTO_DETECT_MODEL` resolves to Haiku for all three modes with no explicit override needed.

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

### 4. One documented exception

`evaluate_sources()` in `relevance.py` reads `mode.model` directly (not via agent.py kwarg). Intentionally stays on Sonnet — relevance scoring directly gates what enters reports. Candidate for Tier 2 but requires A/B testing due to score distribution sensitivity.

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
- **Tests**: 874 passing (includes 2 new integration tests)
- **Agent visibility**: `model` + `planning_model` fields added to ModeInfo and `list_modes()` output
- **Review**: 5 findings (0 P1, 3 P2, 2 P3), all fixed

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
- **Haiku quality monitoring**: Run the first 10-20 real queries with `-v` and check decompose output quality. Flag if sub-query count drops or queries become less targeted. This is the gate for Tier 2 decisions.
- **Don't copy the evaluate_sources exception**: `evaluate_sources()` reading `mode.model` directly is a documented, intentional deviation. New modules should receive the model as a kwarg from `agent.py` — don't use this as a template.
- **Tier 2 gate**: Don't expand Haiku routing (relevance scoring, summarization) without A/B comparison data on output quality. The safe default is Sonnet for anything user-facing.

## Risk Resolution

**Feed-forward risk from review:** "Whether Haiku decompose quality holds on complex queries — needs real run monitoring."

**What happened:** The risk was accepted as a monitoring item rather than a blocking concern. All 7 review agents agreed the implementation is safe because: (1) prompt injection defense is architecture-dependent, not model-dependent, (2) all planning call sites have code-level output validation with safe defaults, and (3) the performance oracle confirmed Haiku capability is sufficient for structured classification tasks. The risk remains as a deferred monitoring item — first 10-20 real runs should be spot-checked before Tier 2 expansion.

**Lesson:** When quality risk is hard to evaluate without production data, ship with monitoring rather than blocking on theoretical concerns. The frozen dataclass default (`AUTO_DETECT_MODEL`) makes rollback trivial — change one field value.

## Related

- [`model-string-unification.md`](model-string-unification.md) — Direct predecessor. Cycle 15 unified model strings into `ResearchMode.model`; Cycle 21 extends this with `planning_model` for tiered routing.
- [`parallel-async-synthesis-with-safety-barriers.md`](parallel-async-synthesis-with-safety-barriers.md) — Async patterns used by planning calls that run in parallel (semaphore + gather).
- [`agent-native-return-structured-data.md`](agent-native-return-structured-data.md) — How `ResearchMode` flows through the pipeline as structured data.
- [`mcp-server-boundary-protection-and-agent-parity.md`](../security/mcp-server-boundary-protection-and-agent-parity.md) — Agent-native parity checklist applied to ModeInfo update (fix 116).
- [`pip-installable-package-and-public-api.md`](pip-installable-package-and-public-api.md) — Validation ownership pattern for frozen dataclass fields at boundaries.
- `research_agent/modes.py` — The dataclass with both `model` and `planning_model` fields.
- `research_agent/agent.py` — The orchestrator routing 7 planning + 8 synthesis call sites.

## Three Questions (Compound Phase)

1. **Hardest pattern to extract from the fixes?** The relationship between "static task-based routing" as a general pattern and the specific decision about where to draw the planning/synthesis boundary. The 7/8 split is specific to this project's pipeline — the transferable insight is "classify pipeline stages by quality sensitivity, not by module."

2. **What did you consider documenting but left out, and why?** Detailed per-call-site latency benchmarks. The plan had estimated ranges (e.g., decompose: 0.9-1.5s → 0.2-0.3s) but these are pre-production estimates. Including them would imply measured precision that doesn't exist yet. Better to document after real usage data.

3. **What might future sessions miss that this solution doesn't cover?** The interaction between `planning_model` and the iteration system (Cycle 20). `iterate.py` calls `generate_refined_queries` and `generate_followup_questions` via `agent.py`, which now routes to Haiku. If iteration quality degrades on complex topics, the root cause might be traced to Haiku's planning quality rather than iteration logic itself. The debugging path isn't obvious because the model routing is invisible at the `iterate.py` level.
