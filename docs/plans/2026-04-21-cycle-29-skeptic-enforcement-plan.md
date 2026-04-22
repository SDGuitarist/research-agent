---
title: "Cycle 29: Verification & Synthesis Integrity"
type: feat
status: active
date: 2026-04-21
origin: docs/research/2026-03-09-entropy-fixes-roadmap.md
feed_forward:
  risk: "Search coverage dependency — epistemic rigor sits on Tavily + DDG results. C33 should include coverage confidence or accept as structural risk."
  verify_first: true
---

# Cycle 29: Verification & Synthesis Integrity

## Prior Phase Risk

> "Search coverage dependency — the entire epistemic rigor thesis sits on top of Tavily + DuckDuckGo results. If coverage is thin, adversarial verification operates on an incomplete evidence base."

**Decision:** Accept as structural risk for C29. Coverage confidence is a C33 concern (confidence scoring), not a C29 concern (skeptic enforcement). C29 makes the pipeline honest about what it *finds*; C33 will later make it honest about what it *missed*. Attempting to address coverage in C29 would mix concerns — skeptic enforcement is about verifying claims, not evaluating search breadth.

## Overview

Three items from the entropy roadmap, all targeting the gap between what the skeptic detects and what appears in the final report:

1. **Skeptic enforcement** — Parse `[Critical Finding]` markers from skeptic output, pass as structured data to `synthesize_final()`, add synthesis instructions requiring critical findings to be addressed or marked `[Disputed]`
2. **Score-aware refinement** — Before `refine_query()`, check first-pass score distribution. If all scores <= 2, skip summary-based refinement and use noun-phrase extraction instead
3. **Evidence-tier labeling** — Add synthesis prompt instructions requiring the model to label each claim as documented/inference/illustrative/speculative. Design the data model to be extensible to per-claim confidence scores (C33 seed)

## What exactly is changing?

| # | Item | Module(s) | What Changes | Est. Size |
|---|------|-----------|-------------|-----------|
| 29-1 | Parse skeptic critical findings | `skeptic.py` | New `extract_critical_findings(findings: list[SkepticFinding]) -> tuple[str, ...]` — parse `[Critical Finding]` markers from `checklist` text, return deduplicated tuple of finding texts | ~25 lines |
| 29-2 | Thread critical findings to synthesis | `agent.py` | After skeptic pass (lines 888-909), call `extract_critical_findings()`. Pass result as new `critical_findings: tuple[str, ...] = ()` parameter to `synthesize_final()` | ~10 lines |
| 29-3 | Enforce in synthesis prompt | `synthesize.py` | In `synthesize_final()`, when `critical_findings` is non-empty: (a) add `<critical_findings>` XML block with sanitized findings, (b) add instruction: "Each critical finding MUST be addressed. Either remove the claim, mark it `[Disputed]` with reasoning, or provide additional evidence. Do not ignore critical findings." | ~30 lines |
| 29-4 | Score distribution check | `agent.py` | In `_research_with_refinement()` (line 997), before calling `refine_query()`: compute max score from pass1 results using `evaluate_sources()` data. If all scores <= 2, skip `refine_query()` and use noun-phrase fallback | ~20 lines |
| 29-5 | Noun-phrase fallback | `search.py` | New `extract_noun_phrases(query: str) -> str` — extract noun phrases from original query, recombine as a simpler search query. Uses `validate_query_list()` for validation. No LLM call — regex/heuristic based | ~30 lines |
| 29-6 | Score-aware gate in deep mode | `agent.py` | In `_research_deep()` (line 1069), same check: if pass 1 max score <= 2, use noun-phrase refinement for pass 2 instead of summary-based | ~10 lines |
| 29-7 | Evidence-tier labeling prompt | `synthesize.py` | Add to `synthesize_report()` and `synthesize_final()` prompt instructions: "For each factual claim, indicate its evidence basis using one of: `[Documented]` (directly stated in sources), `[Inferred]` (reasonable inference from limited data), `[Illustrative]` (example for context, not a primary finding), `[Speculative]` (plausible but not source-supported). Place the label at the end of the sentence or paragraph containing the claim." | ~20 lines |
| 29-8 | Evidence tier data model (C33 seed) | `synthesize.py` or new `evidence.py` | Define `EVIDENCE_TIERS: Final[tuple[str, ...]] = ("documented", "inference", "illustrative", "speculative")` as a shared constant. This is the vocabulary C33 will later build `ClaimConfidence` on. Keep it minimal — just the constant, no data classes yet. | ~5 lines |

**Total: ~150 lines across 3 modules (skeptic.py, agent.py, synthesize.py, search.py)**

## What must not change?

- All 1040 existing tests pass
- Existing report format is backward compatible (new `[Disputed]` and `[Documented]`/`[Inferred]` markers are additive)
- Quick mode behavior unchanged (no skeptic, no score-aware refinement)
- `SkepticFinding` dataclass interface unchanged (new function extracts from existing `checklist` field)
- `synthesize_final()` existing parameters unchanged (new `critical_findings` has a default)
- `refine_query()` interface unchanged (caller decides whether to call it)
- Existing skeptic prompts unchanged (enforcement reads existing output, doesn't change what the skeptic produces)

## How will we know it worked?

### Acceptance Tests (EARS)

#### Skeptic Enforcement (29-1 through 29-3)
- WHEN skeptic output contains `[Critical Finding]` markers THE SYSTEM SHALL extract them as a structured tuple of finding texts
- WHEN skeptic output contains no `[Critical Finding]` markers THE SYSTEM SHALL pass an empty tuple to `synthesize_final()`
- WHEN `critical_findings` is non-empty THE SYSTEM SHALL include a `<critical_findings>` XML block in the synthesis prompt
- WHEN the synthesis prompt includes critical findings THE SYSTEM SHALL instruct the model to address each one (remove, mark `[Disputed]`, or provide evidence)
- WHEN skeptic review fails (SkepticError caught at agent.py:906) THE SYSTEM SHALL pass empty critical findings (graceful degradation, existing behavior)
- WHEN mode is quick THE SYSTEM SHALL skip skeptic entirely (existing behavior, unchanged)

#### Score-Aware Refinement (29-4 through 29-6)
- WHEN all first-pass source scores are <= 2 THE SYSTEM SHALL skip `refine_query()` and use noun-phrase extraction from the original query instead
- WHEN at least one first-pass source scores > 2 THE SYSTEM SHALL proceed with `refine_query()` as normal (existing behavior)
- WHEN noun-phrase extraction produces a valid query (3-8 words, passes `validate_query_list()`) THE SYSTEM SHALL use it for pass 2
- WHEN noun-phrase extraction fails to produce a valid query THE SYSTEM SHALL use the original query for pass 2 (safe fallback)
- WHEN mode is quick with decompose=False THE SYSTEM SHALL skip refinement entirely (existing behavior, unchanged)

#### Evidence-Tier Labeling (29-7 through 29-8)
- WHEN synthesizing a standard or deep mode report THE SYSTEM SHALL include evidence-tier labeling instructions in the synthesis prompt
- WHEN synthesizing a quick mode report THE SYSTEM SHALL include evidence-tier labeling instructions (labels are prompt-level, no extra cost)
- WHEN the `EVIDENCE_TIERS` constant is imported THE SYSTEM SHALL provide the four canonical tier names for C33 to build on

### Verification Commands
- `python3 -m pytest tests/ -v` — all 1040+ tests pass
- `python3 -m pytest tests/test_skeptic.py -v -k critical` — new critical finding extraction tests
- `python3 -m pytest tests/test_synthesize.py -v -k tier` — new evidence-tier tests
- `python3 -m pytest tests/test_search.py -v -k noun_phrase` — new noun-phrase extraction tests

## What is the most likely way this plan is wrong?

1. **Skeptic output parsing is fragile.** The `[Critical Finding]` marker is text the LLM produces — it's not guaranteed to be consistent. The existing `_count_severity()` function already counts these markers, so the pattern is proven, but extraction (not just counting) may need fuzzy matching if the model occasionally writes "Critical finding" (lowercase) or "**Critical Finding**" (bold).

2. **Score-aware refinement may trigger too aggressively.** If Tavily returns low scores for a legitimate query (e.g., a very niche topic with thin web coverage), skipping summary-based refinement and falling back to noun phrases could produce *worse* pass 2 results than the summary-based refinement would have. Mitigation: the noun-phrase fallback is a strictly simpler query, not a worse one — it reduces the chance of the refinement adding noise.

3. **Evidence-tier labels may not survive synthesis.** The model may produce labels inconsistently or forget them in longer reports. This is a prompt-level instruction with no enforcement mechanism in C29. C33 (confidence scoring) adds the enforcement layer by extracting and validating labels post-synthesis. C29 introduces the vocabulary; C33 enforces it.

## Implementation Sessions

### Session 1: Skeptic Enforcement (~65 lines)

**Files:** `skeptic.py`, `synthesize.py`, `agent.py`

1. Add `extract_critical_findings(findings: list[SkepticFinding]) -> tuple[str, ...]` to `skeptic.py`
   - Case-insensitive search for `[Critical Finding]` in each finding's `checklist`
   - Extract the text following each marker (to end of line)
   - Deduplicate by normalized text
   - Return as frozen tuple
2. Add `critical_findings: tuple[str, ...] = ()` parameter to `synthesize_final()` in `synthesize.py`
   - When non-empty: build `<critical_findings>` XML block with `sanitize_content()`
   - Add enforcement instruction to the prompt (after `skeptic_instruction`)
3. Thread in `agent.py`: after skeptic pass (line ~909), call `extract_critical_findings(findings)`, pass to `synthesize_final()` call (line ~916)

**Tests (~10):**
- Extract from skeptic output with 0, 1, 3 critical findings
- Case-insensitive matching ("critical finding" vs "Critical Finding")
- Deduplication of identical findings across lenses
- `synthesize_final()` with empty vs populated critical_findings
- XML block contains sanitized content
- Integration: critical findings appear in synthesis prompt

**Commit:** `feat(29-1): enforce skeptic critical findings in synthesis`

### Session 2: Score-Aware Refinement (~60 lines)

**Files:** `agent.py`, `search.py`

1. Add `extract_noun_phrases(query: str) -> str` to `search.py`
   - Split query into words, filter stopwords (prebuilt frozenset)
   - Recombine remaining meaningful words
   - Validate with `validate_query_list()` (reuse existing validation)
   - Return original query if extraction produces nothing valid
2. In `_research_with_refinement()` (agent.py line ~997): before `refine_query()` call, check if evaluation data is available. If not (scores computed later in pipeline), use a lightweight pre-check: if all pass1 snippets are very short (<50 chars avg), treat as low-quality. Otherwise, standard refinement proceeds.

**Design note:** The entropy roadmap says "check first-pass score distribution" but scores are computed in `evaluate_sources()` which runs AFTER fetch/extract/summarize — not after the initial search. The pass1 results at line 997 only have URLs and snippets, not scores. Two options:
   - **Option A:** Run a lightweight pre-scoring on snippets before refinement (adds ~1 LLM call)
   - **Option B:** Use snippet quality as a proxy — short/empty snippets correlate with low relevance
   
   **Choose Option B** — no additional API cost, and the correlation is strong enough (empty snippets → low relevance → summary-based refinement would amplify noise). The plan phase should note this tradeoff for the Codex reviewer.

3. Same logic in `_research_deep()` for pass 2 refinement

**Tests (~8):**
- Noun-phrase extraction from various query formats
- Stopword removal
- Fallback to original query when extraction fails
- Score-aware gate skips refinement on low-quality pass1 (short snippets)
- Score-aware gate allows refinement on high-quality pass1

**Commit:** `feat(29-2): score-aware refinement with noun-phrase fallback`

### Session 3: Evidence-Tier Labeling (~25 lines)

**Files:** `synthesize.py`

1. Define `EVIDENCE_TIERS` constant (shared vocabulary for C33)
2. Add evidence-tier instruction block to `synthesize_report()` — append to `mode_instructions`
3. Add evidence-tier instruction block to `synthesize_final()` — append to synthesis instructions
4. Instruction text: "For each factual claim in the report, indicate its evidence basis using exactly one of these labels at the end of the claim: `[Documented]`, `[Inferred]`, `[Illustrative]`, `[Speculative]`. Use `[Documented]` when the claim is directly stated in a source. Use `[Inferred]` when it is a reasonable inference from limited data. Use `[Illustrative]` when the claim is an example for context. Use `[Speculative]` when it is plausible but not source-supported."

**Tests (~6):**
- `EVIDENCE_TIERS` constant contains exactly 4 values
- Evidence-tier instruction appears in `synthesize_report()` prompt
- Evidence-tier instruction appears in `synthesize_final()` prompt
- Labels are additive (don't break existing report format tests)

**Commit:** `feat(29-3): evidence-tier labeling in synthesis prompts`

### Session 4: Integration Testing (~10 lines test fixtures)

1. Run full test suite: `python3 -m pytest tests/ -v`
2. Verify no regressions in existing synthesis tests
3. Add integration test: mock skeptic output with `[Critical Finding]`, verify it flows through to synthesis prompt
4. Verify evidence-tier instruction doesn't appear in `synthesize_draft()` (draft is objective, no tier labels)

**Commit:** `test(29-4): integration tests for skeptic enforcement and evidence tiers`

## Dependencies & Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| `[Critical Finding]` parsing fragility | MEDIUM | Case-insensitive matching. Existing `_count_severity()` proves the pattern works. Add fuzzy matching if needed in review. |
| Score-aware refinement uses snippet proxy, not actual scores | LOW | Snippet quality correlates with relevance. No additional API cost. Document as design choice for reviewer. |
| Evidence-tier labels inconsistent in model output | LOW | C29 introduces vocabulary; C33 adds enforcement. Prompt-level-only in C29 is acceptable. |
| New `critical_findings` param on `synthesize_final()` breaks callers | LOW | Default `= ()` means all existing callers work unchanged. |

## Feed-Forward

- **Hardest decision:** Score-aware refinement timing. Scores aren't available when refinement happens (they're computed after fetch/extract/summarize). Chose snippet-quality proxy over adding an LLM pre-scoring call. Less accurate but zero additional cost.
- **Rejected alternatives:** (1) Moving `evaluate_sources()` earlier in the pipeline — would require refactoring the entire standard/deep flow. (2) Adding a lightweight pre-scoring LLM call — adds ~$0.02 per run for marginal improvement. (3) Storing evidence tiers as structured data in C29 — premature; C33 builds the data model. C29 just introduces the vocabulary.
- **Least confident:** Whether the model will consistently produce evidence-tier labels in longer reports. Short reports (quick mode, ~300 words) are likely fine. Deep mode reports (~3500 words) may see label drift in later sections. C33's post-synthesis extraction pass will catch and correct this — but until C33, labels are advisory only.

## Three Questions

1. **Hardest decision in this session?** The snippet-quality proxy for score-aware refinement. The entropy roadmap assumed scores were available at refinement time, but they aren't — `evaluate_sources()` runs after `_fetch_extract_summarize()`. Using snippet length as a proxy is imperfect but avoids adding an LLM call.
2. **What did you consider changing but left alone, and why?** The skeptic prompts themselves. It was tempting to make the skeptic produce more structured output (JSON instead of markdown checklists). But the current format is proven across 10+ cycles, and `extract_critical_findings()` can parse what already exists without changing the skeptic's behavior.
3. **Least confident about going into work?** Evidence-tier label consistency in long reports. The instruction is clear, but long synthesis (3500+ words) may see the model "forget" to label claims in later sections. This is acceptable for C29 (prompt-level only) because C33 adds the enforcement layer. But if the work session reveals that labels are consistently absent in deep mode, we may need to add a reminder instruction at the midpoint of the synthesis prompt.

## Codex Plan Review Handoff

```
Read these files first for project context:
  - HANDOFF.md
  - CLAUDE.md
  - docs/plans/2026-04-21-cycle-29-skeptic-enforcement-plan.md

Review this plan for:
1. Gaps — does the snippet-quality proxy for score-aware refinement hold
   up? The entropy roadmap assumed actual score data was available at
   refinement time. This plan uses snippet length as a proxy instead.
   Is that defensible, or should we add a pre-scoring step?
2. Wrong assumptions — does synthesize_final() actually receive the
   skeptic findings at the right point in the pipeline? Verify against
   agent.py lines 888-928.
3. Scope creep — is the EVIDENCE_TIERS constant (29-8) truly minimal
   enough for a C33 seed, or does it prematurely constrain the C33
   data model?
4. The Feed-Forward "least confident" — evidence-tier label drift in
   long reports. Is this risk acceptable for C29, or should the plan
   include a mitigation (e.g., mid-report reminder prompt)?
5. Plan Quality Gate — does it answer: what's changing (8 items),
   what must not change (7 invariants), how we'll know (EARS + commands),
   most likely way wrong (3 risks)?

Key files to check:
  - research_agent/skeptic.py (lines 34-39: _count_severity pattern)
  - research_agent/synthesize.py (lines 578-608: current skeptic integration)
  - research_agent/agent.py (lines 888-928: skeptic flow)
  - research_agent/search.py (lines 214-253: refine_query)

Brainstorm doc: docs/brainstorms/2026-04-21-ten-steps-ahead-brainstorm.md

Output: findings + updated Claude Code handoff prompt if plan needs changes.
```
