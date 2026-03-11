# Research Agent Entropy Fixes Roadmap

## Overview

13 items across 5 implementation cycles, following dependency order. The original 10 entropy audit findings are supplemented by 3 features derived from an exploratory study on prompt-induced epistemic calibration (temperature controls, evidence-tier labeling, pre-summary abstention gate, novelty-biased decomposition).

Current cycle: **26** (MCP parity lint — complete)
Roadmap starts at: **Cycle 27**

### Design Principles (from Epistemic Calibration Study)

1. **Prompt semantics before generation controls** — system prompts determine the conceptual basin; temperature only affects stylistic exploration within it.
2. **Upstream fixes before downstream fixes** — cleaner input makes every downstream improvement more effective and reduces false positives.
3. **Epistemic friction over blanket refusal** — skeptical prompts should raise the threshold for confident continuation, not collapse into refusal. Validated by citation-resistance tests showing accurate summaries of real papers alongside refusal of fabricated ones.

---

## Cycle 27: Input Validation & Generation Controls

**Theme:** Prevent bad data from entering the pipeline. Tune generation knobs.

These are the foundation fixes. Every downstream improvement benefits from cleaner input. Temperature controls are bundled here because they modify the same frozen dataclass (`ResearchMode` in `modes.py`) and are low-effort additions validated as secondary to prompt design.

| # | Finding | Module | What Changes | Est. Size |
|---|---------|--------|-------------|-----------|
| 1 | Vague query detection | `decompose.py` | Add pre-decomposition validation — reject queries with <3 meaningful words, no domain-specific terms. Return user-facing message requesting clarification. | ~60 lines |
| 8 | Idempotent sanitization | `sanitize.py` | Replace manual `str.replace()` with `html.escape()` or add already-sanitized check. Update all call sites if interface changes. | ~30 lines |
| new | Per-task temperature controls | `modes.py`, all `messages.create()` call sites | Add `temperature`, `planning_temperature`, `synthesis_temperature` fields to `ResearchMode`. Low temp (0.2-0.3) for classification tasks (relevance, decomposition, validation). Mid temp (0.5) for summarization. Higher temp (0.7-1.0) for skeptic adversarial checks and synthesis. Pass to ~15 call sites. | ~40 lines |

**Why this order:** Finding #1 is the highest-impact single fix — it stops noise at the source. Finding #8 is a data corruption bug that affects every pipeline stage. Temperature is bundled because it touches `modes.py` (same file as #1's config) and follows the established `planning_model`/`relevance_model` pattern from Cycle 21.

**Evidence:** Epistemic calibration study §3.2 — "prompt wording did more to determine the conceptual basin than temperature did. Temperature mainly affected stylistic exploration and token-level boldness inside a region already selected by prompt semantics."

**Acceptance criteria:**
- Queries like "stuff", "what's up", "things" are rejected with a helpful message
- `sanitize_content(sanitize_content(text)) == sanitize_content(text)` for all inputs
- Temperature values are passed to all `messages.create()` call sites
- Low-temperature tasks (relevance, decomposition) produce stable outputs across runs
- All 938+ existing tests still pass
- New tests cover edge cases: single-word queries, punctuation-only, hyphenated terms

**Estimated sessions:** 3 (vague query detection, idempotent sanitization, temperature controls)

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

These fixes close the gap between what the skeptic detects and what appears in the final report. Evidence-tier labeling is added here because it pairs with skeptic enforcement — both shape how synthesis handles confidence levels.

| # | Finding | Module | What Changes | Est. Size |
|---|---------|--------|-------------|-----------|
| 7 | Enforce skeptic findings | `synthesize.py`, `skeptic.py` | Parse skeptic output for `[Critical Finding]` markers. Pass structured list to `synthesize_final()`. Add synthesis instruction: critical findings must be removed or marked disputed. | ~80 lines |
| 10 | Score-aware refinement | `search.py`, `agent.py` | Before calling `refine_query()`, check first-pass score distribution. If all scores <= 2, skip summary-based refinement — use noun-phrase extraction from original query instead. | ~60 lines |
| new | Evidence-tier labeling | `synthesize.py` | Add synthesis prompt instructions requiring the model to categorize each claim as: documented finding, inference from limited data, illustrative example, or speculative. Labels appear inline in the report so the reader sees evidence strength. | ~30 lines |

**Why this order:** #7 is the most impactful — it directly prevents hallucination from reaching the user. #10 prevents the refinement loop from amplifying noise. Evidence-tier labeling complements both: skeptic enforcement tells the synthesizer what to distrust, tier labeling tells it how to present what it does trust.

**Evidence:** Epistemic calibration study §3.1 — "When examples were further constrained to be labeled as documented or illustrative, the model became more disciplined and less likely to overstate uncertain examples as factual."

**Dependencies:** Cycle 28's stricter relevance cutoff means the skeptic receives higher-quality sources, so its critical findings are more meaningful (fewer false alarms from noisy sources). Evidence-tier labeling is most valuable when the sources reaching synthesis have already passed quality gates.

**Acceptance criteria:**
- When skeptic flags `[Critical Finding]`, the corresponding claim in the final report is either removed or marked with `[Disputed]` + reasoning
- Refinement skips summary-based approach when first pass scores are all <= 2
- Noun-phrase fallback produces valid search queries (validated with existing `validate_query_list()`)
- Synthesis output includes evidence-tier labels for claims (documented/inference/illustrative/speculative)
- Deep mode e2e test: inject a source with a verifiably false claim, confirm skeptic catches it and synthesis marks it

**Estimated sessions:** 4 (skeptic enforcement, score-aware refinement, evidence-tier labeling, integration testing)

---

## Cycle 30: Summarization & Context Preservation

**Theme:** Preserve signal through the middle of the pipeline.

These are the highest-effort fixes and benefit most from all previous cycles being in place. The pre-summary abstention gate is added here because it modifies summarization behavior and works best when upstream filters (input validation, relevance cutoff, snippet tiering, skeptic enforcement) are already in place — fewer false refusals.

| # | Finding | Module | What Changes | Est. Size |
|---|---------|--------|-------------|-----------|
| 3 | Source diversity gate | `relevance.py` | After scoring, count distinct domains among passing sources. Require minimum unique domains: 2 (quick), 3 (standard), 4 (deep). If unmet, downgrade to short_report. | ~50 lines |
| 4 | Cross-chunk context | `summarize.py` | Pass chunk index, total chunks, and one-sentence prior-chunk summary to each summarization call. Modify `_summarize_chunk()` prompt to include context header. | ~40 lines |
| 5 | Sentence-boundary truncation | `token_budget.py` | Replace character-level truncation with sentence-boundary truncation (find last `.` before limit). Add structured truncation marker with percentage removed. | ~40 lines |
| new | Pre-summary abstention gate | `summarize.py` or `synthesize.py` | Add system prompt instructing the model: if a source makes a specific factual claim (statistic, date, named study, quote) not corroborated by other sources in the batch, flag it rather than presenting as confirmed. Cross-source consistency checking at the prompt level. Placement (per-source summarization vs. synthesis) needs planning. | ~50 lines |

**Why this order:** #3 (diversity) is a gate change that affects which sources reach synthesis — do it first so #4 and #5 operate on a diverse source set. #4 (chunking) and #5 (truncation) are independent of each other. Pre-summary abstention runs last because its placement depends on how cross-chunk context (#4) is implemented.

**Evidence:** Epistemic calibration study §3.5 — "The model refused to summarize a fabricated citation, then refused again on plausible-but-fake citations... Yet when asked to summarize a real paper, it produced a substantively accurate summary." Study §6 recommends "abstention protocols for unverifiable citations before allowing summary generation."

**Design note:** Confidence on the abstention gate is 75%. The mechanism is validated by the study, but summarization happens per-source in batches — the model may not have cross-source context at that stage. May need to live in `synthesize.py` instead, where all summaries are visible. Planning phase must resolve placement.

**Dependencies:** Cycles 27-29 ensure that by the time sources reach these stages, they are (a) based on meaningful queries, (b) relevance-filtered at a higher bar, (c) quality-tiered, and (d) skeptic-verified. These fixes preserve signal that earlier cycles ensured was actually signal.

**Acceptance criteria:**
- Reports that cite 4+ sources from the same domain are downgraded to short_report
- Chunk summaries reference prior chunk content when applicable
- Truncation never cuts mid-sentence
- Truncation marker includes percentage of content removed
- Uncorroborated specific claims (stats, dates, named studies) are flagged rather than presented as confirmed
- No over-refusal: corroborated claims and general analysis pass through normally
- No regression on existing test suite

**Estimated sessions:** 4 (diversity gate, cross-chunk context, sentence truncation, abstention gate)

---

## Cycle 31: Research Distinctiveness

**Theme:** Make the agent's output worth more than a single Claude prompt.

These are enhancements, not fixes. Novelty-biased decomposition pushes the agent past centroid-level research. The MCP tools are promoted here per the promote-or-drop rule (deferral #2).

| # | Finding | Module | What Changes | Est. Size |
|---|---------|--------|-------------|-----------|
| new | Novelty-biased decomposition | `decompose.py` | Add decomposition mode (tied to `--deep`) where 1-2 sub-queries are explicitly novelty-biased: "What aspects of [topic] are underrepresented in mainstream coverage?" Pushes search into longer-tail territory. | ~40 lines + A/B testing |
| 123 | MCP `--cost` + `--critique-history` tools | `mcp_server.py` | Add missing MCP tools for cost estimation and critique history. Promote-or-drop triggered (deferral #2). | ~80 lines |

**Why together:** Both are enhancements that add capability without fixing existing bugs. Bundling gives the cycle enough scope to justify the full compound loop.

**Evidence:** Epistemic calibration study §3.1 — "Prompts asking for 'mechanisms most people overlook' reliably moved the model into a more distinctive explanatory region."

**Design note:** Confidence on novelty decomposition is 70%. The prompting technique is validated, but search engines may not surface good results for novelty-framed queries. A/B testing is mandatory — compare decomposition output and search result quality between standard and novelty-biased sub-queries.

**Dependencies:** With Cycles 27-30 complete, the pipeline produces clean, well-filtered, evidence-labeled reports. Novelty decomposition adds value on top of that foundation rather than fighting noise.

**Acceptance criteria:**
- Deep mode generates at least 1 novelty-biased sub-query per research run
- A/B test: 10 queries comparing standard vs. novelty decomposition on search result diversity and report distinctiveness
- MCP `--cost` tool returns accurate per-mode cost estimates
- MCP `--critique-history` tool returns structured critique data
- No regression in standard/quick mode behavior

**Estimated sessions:** 3 (novelty decomposition + A/B test, MCP tools, integration testing)

---

## Dependency Map

```
Cycle 27: Input Validation & Generation Controls
├── #1 Vague query detection
├── #8 Idempotent sanitization
└── NEW: Per-task temperature controls
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
├── #10 Score-aware refinement (depends on #2: score distribution meaningful after cutoff change)
└── NEW: Evidence-tier labeling (pairs with #7: how to present what the skeptic trusts)
         │
         ▼
Cycle 30: Summarization & Context Preservation
├── #3 Source diversity gate (depends on #2: scoring must be solid before adding diversity check)
├── #4 Cross-chunk context
├── #5 Sentence-boundary truncation
└── NEW: Pre-summary abstention gate (needs all upstream filters to avoid false refusals)
         │
         ▼
Cycle 31: Research Distinctiveness
├── NEW: Novelty-biased decomposition (benefits from clean pipeline foundation)
└── #123 MCP --cost + --critique-history tools (promote-or-drop at deferral #2)
```

---

## Estimated Timeline

| Cycle | Sessions | Scope |
|-------|----------|-------|
| 27 | 3 | 3 items, ~130 lines |
| 28 | 3 | 3 items, ~100 lines + A/B testing |
| 29 | 4 | 3 items, ~170 lines + integration test |
| 30 | 4 | 4 items, ~180 lines |
| 31 | 3 | 2 items, ~120 lines + A/B testing |
| **Total** | **17 sessions** | **15 items, ~700 lines** |

Each cycle follows the full compound engineering loop: brainstorm -> plan -> plan review -> work -> review -> compound.

---

## What's Not on This Roadmap

These were considered but excluded:

- **Relevance score passthrough to synthesizer** — Nice-to-have but the cutoff raise in Cycle 28 addresses the core problem. Revisit if synthesis quality issues persist after Cycle 28.
- **Re-summarization instead of truncation** — Higher effort than sentence-boundary truncation with marginal benefit. The truncation percentage marker gives the synthesizer enough signal to hedge. Revisit if token budget truncation is hit frequently in practice.
- **Context file semantic injection hardening** — Context files are local-only and user-authored. The risk is real but low-priority since the user is the attacker in this scenario. Monitor but don't fix unless context files become shareable.
- **Tier 3 model routing (summarization)** — Deferred indefinitely. Epistemic calibration study reinforces that prompt design matters more than model routing for summarization quality.

## Source References

- Entropy audit: `docs/research/2026-03-09-entropy-and-prompting-report.md`, `docs/research/2026-03-09-research-agent-entropy-audit.md`
- Epistemic calibration study: Prompt-Induced Epistemic Calibration in Large Language Models (exploratory qualitative study, Claude Developer Workbench, 2026)
- Key study findings applied: §3.1 (calibration labeling), §3.2 (temperature as style knob), §3.5 (citation resistance without over-refusal), §6 (abstention protocols)
