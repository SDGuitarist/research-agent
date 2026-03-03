---
title: "feat: Add tiered model routing for planning steps"
type: feat
status: active
date: 2026-03-02
deepened: 2026-03-02
origin: docs/brainstorms/2026-03-02-tiered-model-routing-brainstorm.md
feed_forward:
  risk: "Whether Haiku's decompose quality is good enough for complex multi-topic queries — sub-query generation for nuanced topics might produce less targeted queries, leading to weaker search results downstream."
  verify_first: true
---

# feat: Add tiered model routing for planning steps

## Enhancement Summary

**Deepened on:** 2026-03-02
**Research agents used:** architecture-strategist, kieran-python-reviewer, performance-oracle, code-simplicity-reviewer, pattern-recognition-specialist, security-sentinel, best-practices-researcher, learnings-researcher, repo-research-analyst

### Key Improvements
1. **Corrected cost estimates** — actual savings are ~4-7% (not 8-11%) based on real pricing analysis ($1/$5 vs $3/$15 per MTok = 3x, not 10x)
2. **Added explicit "stays on Sonnet" table** — documents all 8 unchanged call sites to prevent ambiguity during implementation
3. **Improved test strategy** — add routing assertions to existing factory tests instead of 3 new test functions (simpler, same coverage)
4. **Added debug logging** — 7 one-line `logger.debug` calls at changed call sites to enable manual verification
5. **Corrected quick mode documentation** — quick mode does call `refine_query()` via `_research_with_refinement`, so planning_model isn't fully inert there

### New Considerations Discovered
- Security review confirms prompt injection resistance is architecture-dependent (code-level validation), not model-dependent — safe to proceed
- The `refine_query()` function in `search.py` is the only planning call site without output validation (`validate_query_list()`) — pre-existing gap, not introduced by this plan
- `evaluate_sources()` in `relevance.py` reads `mode.model` directly (not via agent.py kwarg) — noted for Tier 2 planning
- Anthropic's own cookbook demonstrates the exact Sonnet-for-synthesis + Haiku-for-classification pattern we're implementing

## Prior Phase Risk

> **Brainstorm "Least confident about":** Whether Haiku's decompose quality is good enough for complex multi-topic queries. Simple classification (SIMPLE/COMPLEX) should be fine, but sub-query generation for nuanced topics might produce less targeted queries, leading to weaker search results downstream.

This plan addresses the risk with a verification step: run 3-5 test queries comparing Haiku vs Sonnet decompose output before shipping. Work phase tackles decompose first so quality can be assessed early.

## Overview

Add a `planning_model` field to `ResearchMode` that routes Haiku to 7 call sites across 6 low-volume planning/classification functions while keeping Sonnet for synthesis and quality-critical steps. Estimated savings: ~4-7% cost per standard run, plus ~3-5 second latency improvement on the critical path.

### Research Insights

**Industry Pattern Validation:**
This is "Static Task-Based Routing" (Pattern A) — the simplest and most common multi-model pattern. Each pipeline step is statically assigned a model at configuration time. Anthropic's own cookbook demonstrates this exact pattern: Sonnet for summarization + Haiku for ranking/scoring within the same application ([anthropic-cookbook/summarization/guide.ipynb](https://github.com/anthropics/anthropic-cookbook/blob/main/capabilities/summarization/guide.ipynb)).

**Haiku vs Sonnet for Planning Tasks (verified pricing, March 2026):**

| Model | Input (per MTok) | Output (per MTok) | Relative cost |
|-------|-----------------|-------------------|---------------|
| Haiku 4.5 | $1.00 | $5.00 | 1x (baseline) |
| Sonnet 4 | $3.00 | $15.00 | 3x |

**Haiku capability assessment per call site (quality risk ranked):**

| Risk | Function | Why |
|------|----------|-----|
| Higher | `decompose_query()` | Sub-query generation for nuanced topics benefits from stronger reasoning |
| Moderate | `identify_coverage_gaps()` | Gap diagnosis requires analytical reasoning about missing topics |
| Low | `generate_refined_queries()` | Structured gap-then-query pattern with validation safety net |
| Low | `generate_followup_questions()` | Pattern-based generation with validation |
| Very low | `refine_query()` | 3-8 word search query, `max_tokens=50`, fill-in-the-blank task |
| Very low | `evaluate_report()` | 1-5 scoring on defined dimensions, metadata only (never user-facing) |

**Why no fallback to Sonnet is needed:** The cascade pattern (try Haiku, escalate to Sonnet on failure) doubles latency on failure cases and adds branching logic. For planning calls costing fractions of a cent, the complexity isn't worth it. If Haiku decomposition quality proves insufficient for certain query types, add a targeted fallback to `decompose_query()` only — not a general framework.

## Proposed Solution

Add one field to the frozen dataclass, update 7 call sites in agent.py, add debug logging at each. No changes to the 6 target modules — they already accept `model` as a kwarg.

### Changes by file

**`modes.py`** — Add field (no cost_estimate changes — defer until real usage data):
```python
planning_model: str = AUTO_DETECT_MODEL  # Cheaper model for planning/classification steps
```
Place after `model` field (line 31) to group model concerns together.

**`agent.py`** — 7 call sites change from `model=self.mode.model` to `model=self.mode.planning_model`:

| # | Function | Line | Client type | Quality risk |
|---|----------|------|-------------|-------------|
| 1 | `decompose_query()` | ~438 | Sync | Higher — verify first |
| 2 | `refine_query()` (standard pass) | ~933 | Sync | Very low |
| 3 | `refine_query()` (deep pass) | ~1003 | Sync | Very low |
| 4 | `identify_coverage_gaps()` | ~657 | Async | Moderate |
| 5 | `generate_refined_queries()` | ~253 | Sync via `to_thread` | Low |
| 6 | `generate_followup_questions()` | ~258 | Sync via `to_thread` | Low |
| 7 | `evaluate_report()` | ~195 | Sync | Very low |

Also add `logger.debug("Planning: %s → %s", function_name, self.mode.planning_model)` at each changed call site for verification and debugging.

### Sites that remain on `self.mode.model` (Sonnet)

| # | Function | Line | Why stays on Sonnet |
|---|----------|------|---------------------|
| 1 | `summarize_all()` | ~616 | High-volume content extraction, quality directly affects report |
| 2 | `synthesize_report()` | ~807 | User-facing output (quick mode) |
| 3 | `synthesize_draft()` | ~827 | User-facing draft generation |
| 4 | `run_deep_skeptic_pass()` | ~837 | Adversarial reasoning requires strong model |
| 5 | `run_skeptic_combined()` | ~845 | Adversarial reasoning requires strong model |
| 6 | `synthesize_final()` | ~859 | User-facing final report |
| 7 | `generate_insufficient_data_response()` | ~788 | User-facing quality explanation |
| 8 | `synthesize_mini_report()` | ~329 | User-facing iteration sections |

Note: `evaluate_sources()` at ~703/~757 receives the full `mode` object and accesses `mode.model` internally (not via kwarg). This stays on Sonnet — relevance scoring directly gates what enters reports. This is a candidate for Tier 2 but requires A/B testing due to score distribution sensitivity.

**`test_modes.py`** — Add `planning_model` assertions to existing factory method tests:
```python
# Add one assert line to each existing factory test (lines 10-47):
assert mode.planning_model == AUTO_DETECT_MODEL
```
This is ~3 lines across 3 existing tests, not 3 new test functions.

### What does NOT change

- `decompose.py`, `search.py`, `coverage.py`, `iterate.py`, `critique.py` — no signature or logic changes (modules receive model as a parameter, stay model-agnostic)
- `auto_detect_context()` in `context.py` — already uses Haiku via its own default (`model: str = AUTO_DETECT_MODEL`), not routed through ResearchMode. Note: this creates two independent paths to Haiku (decoupled by design — `auto_detect_context` runs before ResearchMode is initialized)
- `summarize.py`, `synthesize.py`, `relevance.py`, `skeptic.py` — stay on Sonnet (see brainstorm: "Steps staying on Sonnet")

### Research Insights: Security

**Prompt injection resistance is architecture-dependent, not model-dependent.** The three-layer defense (sanitize content + XML boundaries + system prompt warnings) combined with code-level output validation (`validate_query_list()`, score clamping, safe defaults) means security posture does not meaningfully change when switching from Sonnet to Haiku. All 7 call sites either validate LLM output through `validate_query_list()` / dedicated parsers with safe defaults, or produce output that is metadata/scores with no downstream security impact.

**One pre-existing gap noted:** `refine_query()` in `search.py` does not validate its output through `validate_query_list()` — the refined query string is used directly as a search query. This is not introduced by this plan (exists today with Sonnet) but is marginally more relevant with a less capable model. Low priority: `max_tokens=50` and string-only output limit the attack surface.

### Research Insights: Performance

**Latency improvement (~3-5s on standard mode critical path):**

| Call | Current (Sonnet) | After (Haiku) | Savings |
|------|-----------------|---------------|---------|
| `decompose_query()` | ~0.9-1.5s | ~0.2-0.3s | ~0.7-1.2s |
| `refine_query()` | ~0.8-1.2s | ~0.15-0.25s | ~0.6-1.0s |
| `identify_coverage_gaps()` | ~0.8-1.3s | ~0.2-0.3s | ~0.6-1.0s |
| `max(generate_refined, generate_followup)` | ~1.0-1.5s | ~0.2-0.35s | ~0.8-1.2s |
| `evaluate_report()` | ~0.8-1.2s | ~0.15-0.25s | ~0.6-1.0s |

Against a ~30-60s total run (dominated by search, fetch, summarize, synthesis), this represents a **5-15% wall-clock speedup** — noticeable to the user.

**Corrected cost savings (based on real token analysis):**

| Mode | Current | After Tier 1 | Savings |
|------|---------|-------------|---------|
| Quick | ~$0.12 | ~$0.12 | ~0% (planning calls rarely fire) |
| Standard | ~$0.45 | ~$0.42-0.43 | ~4-7% |
| Deep | ~$0.95 | ~$0.90-0.92 | ~3-5% |

The brainstorm overestimated because planning calls are a small fraction of total token spend — the bulk goes to summarization (12-36 Sonnet calls) and synthesis (3000-8000 output tokens).

## Acceptance Criteria

- [ ] `ResearchMode` has `planning_model` field defaulting to `AUTO_DETECT_MODEL`
- [ ] All three mode factories (`.quick()`, `.standard()`, `.deep()`) include `planning_model` via default
- [ ] 7 agent.py call sites pass `self.mode.planning_model` for planning functions
- [ ] Debug logging added at each changed call site (`logger.debug`)
- [ ] Tests pass: `python3 -m pytest tests/ -v` — all 871+ tests green
- [ ] Existing factory tests include `planning_model` assertions
- [ ] Verification: compare Haiku vs Sonnet decompose output on 3 test queries (manual spot check)
- [ ] Also verify `identify_coverage_gaps` output quality (second-highest blast radius)

## Implementation Order (Single Session)

Work phase tackles the feed-forward risk first (decompose quality):

1. **Add `planning_model` field to `ResearchMode`** in `modes.py` — field definition with inline comment, placed after `model` (~2 lines)
2. **Update agent.py call sites** — 7 changes, `self.mode.model` → `self.mode.planning_model` + debug logging (~14 lines)
3. **Add test assertions** in `test_modes.py` — one `assert mode.planning_model == AUTO_DETECT_MODEL` per factory test (~3 lines)
4. **Run full test suite** — all 871+ tests must pass
5. **Manual verification** — run `python3 main.py --standard "query" -v` on 2-3 test queries, check debug logs to confirm Haiku is being routed correctly and produces reasonable sub-queries

### Research Insights: Implementation Details

**Field placement:** After `model` (line 31) groups model concerns together. Both fields have defaults, so no positional argument ordering risk with the frozen dataclass.

**Quick mode note:** Quick mode gets `planning_model=AUTO_DETECT_MODEL` via default. Although `decompose=False` and `iteration_enabled=False`, quick mode does call `refine_query()` via `_research_with_refinement()` (line ~933) and may call `identify_coverage_gaps()`. Cost impact is negligible (fractions of a cent) but the field is not fully inert.

**No `__post_init__` validation:** Both `model` and `planning_model` are unvalidated strings. If an invalid model string is passed, the Anthropic API returns an error which is caught by existing `except (APIError, ...)` blocks. The model string is code-controlled (factory methods), not user-controlled — there is no path for external input to influence it.

**No `cost_estimate` changes:** Defer until real usage data exists. The current estimates (`~$0.45`, `~$0.95`) are already rough approximations — changing to `~$0.42` and `~$0.90` implies false precision.

## Patterns to Follow (from learnings)

- **Frozen dataclass field** — same pattern as `model`, `cost_estimate`, `followup_questions` (Cycles 14-15). Configuration belongs in a central frozen dataclass, not in per-module constants (docs/solutions/architecture/model-string-unification.md)
- **Agent.py = orchestrator** — modules receive model as parameter, don't look it up themselves. Zero module signature changes; orchestrator-only routing
- **Mock where imported from** — `anthropic.Anthropic`, not the destination module (Cycle 7 lesson)
- **No module-level model mapping** — rejected in brainstorm for good reason (breaks the pattern where agent.py controls all model passing)
- **Parallel async safety** — if planning involves parallel calls, use `asyncio.Semaphore(N)` + `asyncio.gather` + `asyncio.to_thread()` pattern (docs/solutions/architecture/parallel-async-synthesis-with-safety-barriers.md)
- **Never sanitize twice** — `sanitize_content` is NOT idempotent (docs/solutions/security/non-idempotent-sanitization-double-encode.md)

## Sources

- **Origin brainstorm:** [docs/brainstorms/2026-03-02-tiered-model-routing-brainstorm.md](docs/brainstorms/2026-03-02-tiered-model-routing-brainstorm.md) — key decisions: Tier 1 only, `planning_model` field on ResearchMode, no CLI flag, self-critique on Haiku
- **Precedent:** Cycle 15 model string unification (docs/solutions/architecture/model-string-unification.md)
- **Existing Haiku usage:** `AUTO_DETECT_MODEL` in `modes.py:9`, used by `context.py:253`
- **Anthropic model pricing:** [Claude API Pricing](https://platform.claude.com/docs/en/about-claude/pricing) — Haiku 4.5: $1/$5, Sonnet 4: $3/$15 per MTok
- **Anthropic cookbook pattern:** [Legal Document Summarization (Sonnet + Haiku)](https://github.com/anthropics/anthropic-cookbook/blob/main/capabilities/summarization/guide.ipynb)
- **Model routing research:** [Intelligent LLM Routing — Swfte AI](https://www.swfte.com/blog/intelligent-llm-routing-multi-model-ai), [RouteLLM Framework](https://github.com/lm-sys/RouteLLM)
- **Haiku 4.5 capabilities:** [Introducing Claude Haiku 4.5 — Anthropic](https://www.anthropic.com/news/claude-haiku-4-5)

## Feed-Forward

- **Hardest decision:** Whether to update `cost_estimate` values now or defer. Research revealed the brainstorm's 8-11% savings estimates are roughly double the actual ~4-7% (planning calls are a small fraction of total token spend). Decided to defer cost_estimate changes until real usage data exists — avoids false precision on rough numbers.
- **Rejected alternatives:** (1) Adding `validate_query_list()` to `refine_query()` output — pre-existing gap, out of scope for Tier 1. (2) Adding Haiku-to-Sonnet fallback cascade — doubles latency on failure, complexity not justified for low-cost planning calls. (3) Creating 3 new test functions — adding assertions to existing factory tests achieves same coverage with less boilerplate.
- **Least confident:** Whether `identify_coverage_gaps()` on Haiku will correctly classify gap taxonomy types (QUERY_MISMATCH, THIN_FOOTPRINT, ABSENCE). Misclassification leads to either wasted retries or missed coverage. The safe default (NO_RETRY on unknown values) mitigates worst case, but this function should be included in the manual verification alongside decompose.
