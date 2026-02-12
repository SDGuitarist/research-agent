---
title: Adversarial Verification Pipeline for Report Synthesis
date: 2026-02-11
category: logic-errors
tags: [synthesis, verification, adversarial-review, quality-assurance, skeptic-agents]
module: research_agent
symptoms: [unsupported-claims-in-reports, inference-presented-as-observation, unchallenged-analytical-frame, time-sensitive-dynamics-missed]
severity: medium
summary: Replaced single-pass LLM synthesis with draft→skeptic→final pipeline featuring adversarial review agents that verify claim-evidence alignment, timing dynamics, and strategic framing.
---

# Adversarial Verification Pipeline for Report Synthesis

**Cycle 16** | 2026-02-11

## Problem

The research agent's synthesis step was a single LLM call (`synthesize_report()`) that generated the complete report in one pass. This meant:

1. **Claims could be unsupported** — inferences drawn by the LLM were presented alongside direct observations with no distinction
2. **Time-sensitive dynamics were unweighted** — cost of acting now vs. waiting was never challenged
3. **Analytical frame was never questioned** — whether the analysis solved the right problem was never examined
4. **Business context contaminated factual sections** — competitive positioning was injected before any review could catch coloring

No adversarial review existed. The first reader to challenge the report was the human user.

## Root Cause

Architectural: `synthesize_report()` was monolithic — one prompt, one LLM call, one output, no feedback loop. Errors, biases, and unsupported claims propagated directly into the final report.

## Solution

Replace single-pass synthesis with a three-stage pipeline: **Draft → Skeptic → Final**.

### Stage 1: Synthesize Draft

`synthesize_draft()` produces sections 1-8 (objective factual findings). **No business context injected** — keeps factual sections uncolored.

### Stage 2: Skeptic Review

Adversarial agents challenge the draft through three specialized lenses:

| Lens | Purpose |
|------|---------|
| **Evidence Alignment** | Tags each claim as SUPPORTED / INFERRED / UNSUPPORTED |
| **Timing & Stakes** | Evaluates cost of waiting vs. acting; checks if "wait" signals are evidence-based |
| **Strategic Frame ("Break the Trolley")** | Challenges whether the analysis solves the right problem |

Two execution modes:
- **Standard**: `run_skeptic_combined()` — one LLM call, all 3 lenses, single checklist output
- **Deep**: `run_deep_skeptic_pass()` — 3 sequential agents with cumulative findings (each sees prior agents' output)

### Stage 3: Synthesize Final

`synthesize_final()` produces sections 9-12/13 informed by skeptic analysis. **Critical findings MUST be addressed** in recommendations — the prompt enforces this.

### Integration in agent.py

```python
# Standard/deep mode: draft → skeptic → final synthesis
draft = synthesize_draft(client, query, surviving, model=model)

# Skeptic review
if is_deep:
    findings = run_deep_skeptic_pass(client, draft, synthesis_context, model=model)
else:
    finding = run_skeptic_combined(client, draft, synthesis_context, model=model)
    findings = [finding]

# Final synthesis with skeptic findings
report = synthesize_final(client, query, draft, findings, surviving, ...)
```

### New Modules

**`context.py`** — Stage-appropriate context slicing:
- Search stage gets: brand names, geography, search parameters
- Synthesis stage gets: competitive positioning, brand identity, differentiators
- Uses `removeprefix("## ")` instead of buggy `lstrip("# ")`

**`skeptic.py`** — Adversarial review agents:
- `SkepticFinding` dataclass with lens, checklist, critical_count, concern_count
- Retry with backoff on `RateLimitError` and `APITimeoutError`
- All prompts use XML-delimited content blocks for injection safety

### Code Cleanup

- Deleted ~120 lines dead code in `synthesize.py` (old context validation)
- Fixed `lstrip("# ")` bug → `removeprefix("## ")` (lstrip strips characters, not prefixes)
- Consolidated duplicate `_sanitize_for_prompt` → shared `sanitize_content`
- Removed ~170 lines dead tests
- 385 tests pass (16 files changed, +1711/-481 lines)

## Prevention

1. **Multi-pass synthesis for LLM agents.** Require at least two passes (draft → review → final) in any synthesis pipeline. Single-pass synthesis should be the exception (quick mode), not the default.

2. **Use `removeprefix()` for fixed string prefixes.** `lstrip()` strips individual characters from a set — `"## Title".lstrip("# ")` removes `#`, ` `, and `#` independently. Use `removeprefix("## ")` for literal prefix removal. Add this to code review checklist.

3. **Centralized utility audit on every PR.** Before merging, search for duplicate `_helper` functions across modules. If a function exists in 2+ files, extract to a shared module immediately.

4. **Dead code sweep every 2-3 cycles.** Accumulation is inevitable during rapid iteration. Schedule periodic cleanup passes rather than ignoring dead code indefinitely.

5. **Standardize LLM API retry patterns.** Use a shared `_call_with_retry()` helper for all LLM calls. Include backoff for rate limits, configurable timeouts, and specific exception handling.

## Related Documentation

- [`docs/solutions/logic-errors/source-level-relevance-aggregation.md`](source-level-relevance-aggregation.md) — Cycle 15: scoring hierarchical data before downstream decisions
- [`docs/solutions/feature-implementation/cli-quality-of-life-improvements.md`](../feature-implementation/cli-quality-of-life-improvements.md) — Cycle 14: frozen dataclass patterns for mode configuration
- `LESSONS_LEARNED.md` — Full cycle history with key lessons per cycle
- `research_agent/sanitize.py` — Shared sanitization utility (consolidated in Cycle 12, used by skeptic.py)
