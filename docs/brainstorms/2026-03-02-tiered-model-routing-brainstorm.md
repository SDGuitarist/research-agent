# Cycle 21 Brainstorm: Tiered Model Routing

**Date:** 2026-03-02
**Status:** Ready for planning
**Scope:** Tier 1 — planning steps only

## Prior Phase Risk

> **Cycle 20 "Least confident about":** Double-sanitization idempotency risk. `sanitize_content` is not idempotent — calling it twice on `&` produces `&amp;amp;`. Current code avoids this by sanitizing different extracted substrings at each layer. A future refactor piping one layer's output into another could trigger double-encoding.

This cycle does not touch sanitization. The risk remains standing and should be addressed in a future cycle. Noted here for continuity.

## What We're Building

Add a `planning_model` field to `ResearchMode` that routes cheaper Haiku calls to planning/classification steps while keeping Sonnet for synthesis and quality-critical steps. Tier 1 only — 5-6 low-volume planning calls.

### Steps moving to Haiku

| Step | Module | Calls/run | Current cost contribution |
|------|--------|-----------|--------------------------|
| Query decomposition | `decompose.py` | 1 | Low — classification + sub-query generation |
| Query refinement | `search.py` (`refine_query`) | 1 | Low — generate pass-2 search terms |
| Coverage gap analysis | `coverage.py` | 1 | Low — identify missing topics |
| Iteration query generation | `iterate.py` (`generate_refined_queries`) | 1 | Low — generate gap-targeting queries |
| Follow-up question generation | `iterate.py` (`generate_followup_questions`) | 1 | Low — generate user-facing questions |
| Self-critique | `critique.py` (`evaluate_report`) | 1 | Low — score report on 5 dimensions |

### Steps staying on Sonnet

| Step | Module | Why |
|------|--------|-----|
| Chunk summarization | `summarize.py` | Quality directly affects report — high volume (12-36 calls) |
| Relevance scoring | `relevance.py` | Gate for what enters synthesis — mis-scoring pollutes reports |
| Report synthesis | `synthesize.py` | User-facing output quality |
| Mini-report synthesis | `synthesize.py` | User-facing iteration sections |
| Skeptic agents | `skeptic.py` | Adversarial review needs strong reasoning |

Note: `auto_detect_context()` in `context.py` already uses Haiku via `AUTO_DETECT_MODEL`.

## Why This Approach

**Approach A: Add `planning_model` field to ResearchMode.**

- Follows the existing frozen dataclass pattern in `modes.py`
- Single point of configuration — each mode's factory method sets its planning model
- Agent.py already passes `self.mode.model` everywhere; change ~6 call sites to `self.mode.planning_model`
- Minimal coupling — no new abstractions, no module-level lookups

**Rejected alternatives:**
- **Module-level model mapping dict** — Breaks the pattern where agent.py controls all model passing. More coupling for no benefit at 6 call sites.
- **Separate Anthropic clients** — Doubles client management. The `model` parameter already exists on every function, making client-level separation unnecessary.
- **Tier 2 (planning + relevance scoring)** — Deferred. Relevance scoring is a judgment task where Haiku mis-scoring could pollute reports. Needs A/B comparison data first. ~20-25% savings vs medium risk.
- **Tier 3 (planning + relevance + summarization)** — Deferred indefinitely. Summarization quality directly feeds synthesis. Too risky without quality benchmarks.

## Key Decisions

1. **Tier 1 only** — Planning steps save ~6-8% per run with very low quality risk. Future cycles can expand to Tier 2 with proper testing.
2. **`planning_model` field on ResearchMode** — Simple, follows existing patterns, 6 call sites to update.
3. **No CLI flag for model override** — Keep it configuration-in-code. A `--model` flag adds complexity for a rarely-used escape hatch.
4. **Self-critique on Haiku** — It scores the report on 5 dimensions (1-5 scale). This is a structured classification task that Haiku handles well. If critique quality drops, it only affects the self-assessment metadata, not the report itself.
5. **Verification** — Planning phase should define a lightweight quality check (e.g., compare Haiku vs Sonnet decompose output on 3-5 test queries) to catch Tier 1 regressions before shipping.

## Resolved Questions

1. **Should `quick` mode use Haiku for everything?** No — keep quick on Sonnet. Quick mode's quality contract should stay consistent with other modes. Tier 1 doesn't affect quick mode (it has no planning steps). Revisit if a `--cheap` flag is ever requested.

## Estimated Savings

| Mode | Current est. | After Tier 1 | Savings |
|------|-------------|-------------|---------|
| Quick | ~$0.12 | ~$0.12 (no planning steps) | 0% |
| Standard | ~$0.45 | ~$0.40 | ~11% |
| Deep | ~$0.95 | ~$0.87 | ~8% |

Note: Quick mode has no planning steps (decompose=False, iteration=False), so Tier 1 doesn't affect it.

## Feed-Forward

- **Hardest decision:** Whether to include self-critique in the Haiku tier. It's a judgment task, but its output is metadata (scores), not user-facing report content. Decided to include it since degraded critique doesn't affect the report itself.
- **Rejected alternatives:** Tier 2 (relevance scoring) was tempting for the 20-25% savings, but the risk of mis-scored sources polluting reports outweighs the cost benefit without A/B validation data.
- **Least confident:** Whether Haiku's decompose quality is good enough for complex multi-topic queries. Simple classification (SIMPLE/COMPLEX) should be fine, but sub-query generation for nuanced topics might produce less targeted queries, leading to weaker search results downstream.
