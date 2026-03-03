---
title: "feat: Add tiered model routing for planning steps"
type: feat
status: active
date: 2026-03-02
origin: docs/brainstorms/2026-03-02-tiered-model-routing-brainstorm.md
feed_forward:
  risk: "Whether Haiku's decompose quality is good enough for complex multi-topic queries — sub-query generation for nuanced topics might produce less targeted queries, leading to weaker search results downstream."
  verify_first: true
---

# feat: Add tiered model routing for planning steps

## Prior Phase Risk

> **Brainstorm "Least confident about":** Whether Haiku's decompose quality is good enough for complex multi-topic queries. Simple classification (SIMPLE/COMPLEX) should be fine, but sub-query generation for nuanced topics might produce less targeted queries, leading to weaker search results downstream.

This plan addresses the risk with a verification step: run 3-5 test queries comparing Haiku vs Sonnet decompose output before shipping. Work phase tackles decompose first so quality can be assessed early.

## Overview

Add a `planning_model` field to `ResearchMode` that routes Haiku to 6 low-volume planning/classification functions while keeping Sonnet for synthesis and quality-critical steps. Estimated savings: ~8-11% per run with minimal quality risk (see brainstorm: docs/brainstorms/2026-03-02-tiered-model-routing-brainstorm.md).

## Proposed Solution

Add one field to the frozen dataclass, update 7 call sites in agent.py. No changes to the 6 target modules — they already accept `model` as a kwarg.

### Changes by file

**`modes.py`** — Add field + update cost estimates:
```python
planning_model: str = AUTO_DETECT_MODEL  # after line 31
```
Update `cost_estimate` in `.standard()` and `.deep()` factory methods to reflect new pricing.

**`agent.py`** — 7 call sites change from `model=self.mode.model` to `model=self.mode.planning_model`:

| # | Function | Line | Client type |
|---|----------|------|-------------|
| 1 | `decompose_query()` | ~438 | Sync |
| 2 | `refine_query()` (standard pass) | ~933 | Sync |
| 3 | `refine_query()` (deep pass) | ~1003 | Sync |
| 4 | `identify_coverage_gaps()` | ~657 | Async |
| 5 | `generate_refined_queries()` | ~253 | Sync via `to_thread` |
| 6 | `generate_followup_questions()` | ~258 | Sync via `to_thread` |
| 7 | `evaluate_report()` | ~195 | Sync |

**`test_modes.py`** — Add tests:
- `planning_model` field exists on all three modes
- Value equals `AUTO_DETECT_MODEL` (Haiku)
- `planning_model != model` (routing is actually differentiating)

### What does NOT change

- `decompose.py`, `search.py`, `coverage.py`, `iterate.py`, `critique.py` — no signature or logic changes
- `auto_detect_context()` in `context.py` — already uses Haiku via its own default, not routed through ResearchMode
- `summarize.py`, `synthesize.py`, `relevance.py`, `skeptic.py` — stay on Sonnet (see brainstorm: "Steps staying on Sonnet")

## Acceptance Criteria

- [ ] `ResearchMode` has `planning_model` field defaulting to `AUTO_DETECT_MODEL`
- [ ] All three mode factories (`.quick()`, `.standard()`, `.deep()`) include `planning_model`
- [ ] 7 agent.py call sites pass `self.mode.planning_model` for planning functions
- [ ] `cost_estimate` updated on `.standard()` (~$0.40) and `.deep()` (~$0.87)
- [ ] Tests pass: `python3 -m pytest tests/ -v` — all 871+ tests green
- [ ] New tests cover `planning_model` field on all modes
- [ ] Verification: compare Haiku vs Sonnet decompose output on 3 test queries (manual spot check)

## Implementation Order (Single Session)

Work phase tackles the feed-forward risk first (decompose quality):

1. **Add `planning_model` field to `ResearchMode`** in `modes.py` — field definition + factory methods + cost estimates (~15 lines)
2. **Update agent.py call sites** — 7 changes, `self.mode.model` → `self.mode.planning_model` (~7 lines)
3. **Add tests** in `test_modes.py` — field presence, value, differentiation (~15 lines)
4. **Run full test suite** — all 871+ tests must pass
5. **Manual verification** — run `python3 main.py --standard "query"` on 2-3 test queries, check decompose output in verbose logs (`-v`) to confirm Haiku produces reasonable sub-queries

## Patterns to Follow (from learnings)

- **Frozen dataclass field** — same pattern as `model`, `cost_estimate`, `followup_questions` (Cycles 14-15)
- **Agent.py = orchestrator** — modules receive model as parameter, don't look it up themselves
- **Mock where imported from** — `anthropic.Anthropic`, not the destination module (Cycle 7 lesson)
- **No module-level model mapping** — rejected in brainstorm for good reason

## Sources

- **Origin brainstorm:** [docs/brainstorms/2026-03-02-tiered-model-routing-brainstorm.md](docs/brainstorms/2026-03-02-tiered-model-routing-brainstorm.md) — key decisions: Tier 1 only, `planning_model` field on ResearchMode, no CLI flag, self-critique on Haiku
- **Precedent:** Cycle 15 model string unification (docs/solutions/architecture/model-string-unification.md)
- **Existing Haiku usage:** `AUTO_DETECT_MODEL` in `modes.py:9`, used by `context.py:253`

## Feed-Forward

- **Hardest decision:** Whether to validate `planning_model` in `__post_init__`. Decided against it — the existing `model` field has no validation, and adding validation to one but not the other creates inconsistency. Keep them symmetric.
- **Rejected alternatives:** Adding a `--planning-model` CLI debug flag for the verification step. Verbose logging (`-v`) already shows which model is used in API calls — a dedicated flag adds complexity for a one-time check.
- **Least confident:** Whether the cost estimate updates are accurate. The brainstorm estimates (~11% standard, ~8% deep) are rough — actual savings depend on token counts per planning call, which vary by query complexity. The estimates should be verified against real usage after a few runs.
