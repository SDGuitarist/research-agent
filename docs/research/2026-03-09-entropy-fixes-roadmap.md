# Research Agent Entropy Fixes Roadmap

## Overview

10 findings from the entropy audit, organized into 4 implementation cycles following dependency order. Each cycle groups fixes that are logically related, similar in scope, and don't depend on work in later cycles.

Current cycle: **26** (MCP parity lint — in progress)
Roadmap starts at: **Cycle 27**

---

## Cycle 27: Input Validation & Data Integrity

**Theme:** Prevent bad data from entering the pipeline.

These are the foundation fixes. Every downstream improvement benefits from cleaner input.

| # | Finding | Module | What Changes | Est. Size |
|---|---------|--------|-------------|-----------|
| 1 | Vague query detection | `decompose.py` | Add pre-decomposition validation — reject queries with <3 meaningful words, no domain-specific terms. Return user-facing message requesting clarification. | ~60 lines |
| 8 | Idempotent sanitization | `sanitize.py` | Replace manual `str.replace()` with `html.escape()` or add already-sanitized check. Update all call sites if interface changes. | ~30 lines |

**Why this order:** Finding #1 is the highest-impact single fix — it stops noise at the source. Finding #8 is a data corruption bug that affects every pipeline stage. Both are low-effort and independent of each other.

**Acceptance criteria:**
- Queries like "stuff", "what's up", "things" are rejected with a helpful message
- `sanitize_content(sanitize_content(text)) == sanitize_content(text)` for all inputs
- All 938+ existing tests still pass
- New tests cover edge cases: single-word queries, punctuation-only, hyphenated terms

**Estimated sessions:** 2 (one per fix, small commits)

---

## Cycle 28: Relevance & Source Quality Gates

**Theme:** Filter noise before it reaches synthesis.

With clean input from Cycle 27, these fixes ensure that only high-quality, diverse sources reach the report.

| # | Finding | Module | What Changes | Est. Size |
|---|---------|--------|-------------|-----------|
| 2 | Raise relevance cutoff | `modes.py`, `relevance.py` | Raise cutoff to 4 for standard/deep. Keep 3 for quick. A/B test with ~10 queries to verify no decision flips on good sources. | ~20 lines + testing |
| 6 | Snippet quality tier | `cascade.py`, `relevance.py` | Tag snippet-sourced content with `source_tier: "snippet"`. Cap snippet max score at 3. Pass tier to synthesizer. | ~50 lines |
| 9 | Quick mode min sources | `modes.py` | Raise `min_sources_short_report` from 1 to 2 for quick mode. Add confidence indicator to quick-mode report output. | ~30 lines |

**Why this order:** #2 (cutoff) is the broadest filter — raising it reduces the volume of noise reaching synthesis and makes #6 less urgent but still valuable. #6 (snippet tier) prevents thin sources from punching above their weight. #9 (quick mode) is a config change that closes a specific hallucination vector.

**Dependencies:** Cycle 27's vague query detection means fewer garbage queries reach the relevance scorer, so the cutoff change is tested against actually meaningful queries.

**Acceptance criteria:**
- Standard/deep modes reject score-3 sources
- Snippet-sourced content is visibly tagged in relevance output
- Quick mode requires 2+ sources for any report
- A/B test: 10 queries on standard mode, compare gate decisions at cutoff 3 vs 4
- No regression in report quality for well-formed queries

**Estimated sessions:** 3 (cutoff + A/B test, snippet tier, quick mode config)

---

## Cycle 29: Verification & Synthesis Integrity

**Theme:** Ensure the report reflects what the evidence actually supports.

These fixes close the gap between what the skeptic detects and what appears in the final report.

| # | Finding | Module | What Changes | Est. Size |
|---|---------|--------|-------------|-----------|
| 7 | Enforce skeptic findings | `synthesize.py`, `skeptic.py` | Parse skeptic output for `[Critical Finding]` markers. Pass structured list to `synthesize_final()`. Add synthesis instruction: critical findings must be removed or marked disputed. | ~80 lines |
| 10 | Score-aware refinement | `search.py`, `agent.py` | Before calling `refine_query()`, check first-pass score distribution. If all scores ≤ 2, skip summary-based refinement — use noun-phrase extraction from original query instead. | ~60 lines |

**Why this order:** #7 is the more impactful fix — it directly prevents hallucination from reaching the user. #10 prevents the refinement loop from amplifying noise, which improves the quality of sources that reach the skeptic.

**Dependencies:** Cycle 28's stricter relevance cutoff means the skeptic receives higher-quality sources, so its critical findings are more meaningful (fewer false alarms from noisy sources).

**Acceptance criteria:**
- When skeptic flags `[Critical Finding]`, the corresponding claim in the final report is either removed or marked with `[Disputed]` + reasoning
- Refinement skips summary-based approach when first pass scores are all ≤ 2
- Noun-phrase fallback produces valid search queries (validated with existing `validate_query_list()`)
- Deep mode e2e test: inject a source with a verifiably false claim, confirm skeptic catches it and synthesis marks it

**Estimated sessions:** 3 (skeptic enforcement, score-aware refinement, integration testing)

---

## Cycle 30: Summarization & Context Preservation

**Theme:** Preserve signal through the middle of the pipeline.

These are the highest-effort fixes and benefit most from all previous cycles being in place.

| # | Finding | Module | What Changes | Est. Size |
|---|---------|--------|-------------|-----------|
| 3 | Source diversity gate | `relevance.py` | After scoring, count distinct domains among passing sources. Require minimum unique domains: 2 (quick), 3 (standard), 4 (deep). If unmet, downgrade to short_report. | ~50 lines |
| 4 | Cross-chunk context | `summarize.py` | Pass chunk index, total chunks, and one-sentence prior-chunk summary to each summarization call. Modify `_summarize_chunk()` prompt to include context header. | ~40 lines |
| 5 | Sentence-boundary truncation | `token_budget.py` | Replace character-level truncation with sentence-boundary truncation (find last `.` before limit). Add structured truncation marker with percentage removed. | ~40 lines |

**Why this order:** #3 (diversity) is a gate change that affects which sources reach synthesis — do it first so #4 and #5 operate on a diverse source set. #4 (chunking) and #5 (truncation) are independent of each other and can be done in either order.

**Dependencies:** Cycles 27-29 ensure that by the time sources reach these stages, they are (a) based on meaningful queries, (b) relevance-filtered at a higher bar, (c) quality-tiered, and (d) skeptic-verified. These fixes preserve signal that earlier cycles ensured was actually signal.

**Acceptance criteria:**
- Reports that cite 4+ sources from the same domain are downgraded to short_report
- Chunk summaries reference prior chunk content when applicable
- Truncation never cuts mid-sentence
- Truncation marker includes percentage of content removed
- No regression on existing test suite

**Estimated sessions:** 3 (diversity gate, cross-chunk context, sentence truncation)

---

## Dependency Map

```
Cycle 27: Input Validation & Data Integrity
├── #1 Vague query detection
└── #8 Idempotent sanitization
         │
         ▼
Cycle 28: Relevance & Source Quality Gates
├── #2 Raise relevance cutoff (depends on #1: cleaner queries for A/B test)
├── #6 Snippet quality tier
└── #9 Quick mode min sources
         │
         ▼
Cycle 29: Verification & Synthesis Integrity
├── #7 Enforce skeptic findings (depends on #2: fewer noisy sources = fewer false alarms)
└── #10 Score-aware refinement (depends on #2: score distribution meaningful after cutoff change)
         │
         ▼
Cycle 30: Summarization & Context Preservation
├── #3 Source diversity gate (depends on #2: scoring must be solid before adding diversity check)
├── #4 Cross-chunk context
└── #5 Sentence-boundary truncation
```

---

## Estimated Timeline

| Cycle | Sessions | Scope |
|-------|----------|-------|
| 27 | 2 | 2 fixes, ~90 lines |
| 28 | 3 | 3 fixes, ~100 lines + A/B testing |
| 29 | 3 | 2 fixes, ~140 lines + integration test |
| 30 | 3 | 3 fixes, ~130 lines |
| **Total** | **11 sessions** | **10 fixes, ~460 lines** |

Each cycle follows the full compound engineering loop: brainstorm → plan → plan review → work → review → compound.

---

## What's Not on This Roadmap

These were considered but excluded:

- **Relevance score passthrough to synthesizer** — Nice-to-have but the cutoff raise in Cycle 28 addresses the core problem. Revisit if synthesis quality issues persist after Cycle 28.
- **Re-summarization instead of truncation** — Higher effort than sentence-boundary truncation with marginal benefit. The truncation percentage marker gives the synthesizer enough signal to hedge. Revisit if token budget truncation is hit frequently in practice.
- **Context file semantic injection hardening** — Context files are local-only and user-authored. The risk is real but low-priority since the user is the attacker in this scenario. Monitor but don't fix unless context files become shareable.
