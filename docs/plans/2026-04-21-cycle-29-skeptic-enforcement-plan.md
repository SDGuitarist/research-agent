---
title: "Cycle 29: Verification & Synthesis Integrity"
type: feat
status: active
date: 2026-04-21
origin: docs/research/2026-03-09-entropy-fixes-roadmap.md
feed_forward:
  risk: "Search coverage dependency — epistemic rigor sits on Tavily + DDG results. C33 should include coverage confidence or accept as structural risk."
  verify_first: true
revised: 2026-04-21 (Codex review — 5 findings addressed)
---

# Cycle 29: Verification & Synthesis Integrity

## Prior Phase Risk

> "Search coverage dependency — the entire epistemic rigor thesis sits on top of Tavily + DuckDuckGo results. If coverage is thin, adversarial verification operates on an incomplete evidence base."

**Decision:** Accept as structural risk for C29. Coverage confidence is a C33 concern (confidence scoring), not a C29 concern (skeptic enforcement). C29 makes the pipeline honest about what it *finds*; C33 will later make it honest about what it *missed*.

## Overview

Three items from the entropy roadmap, all targeting the gap between what the skeptic detects and what appears in the final report:

1. **Skeptic enforcement** — Extract `[Critical Finding]` markers from existing skeptic output as a structured subset, build a targeted `<critical_findings>` XML block, and add per-finding enforcement instructions that are more specific than the current general "address critical findings" language
2. **Snippet-quality gate for refinement** — In standard mode, skip summary-based `refine_query()` when pass1 snippets indicate poor-quality results (all empty or very short). In deep mode, skip when pass1 summaries indicate poor quality. Use noun-phrase extraction as fallback. Not score-based — scores are unavailable at refinement time.
3. **Evidence-tier labeling** — Add synthesis prompt instructions requiring the model to label each claim as documented/inference/illustrative/speculative. Include a mid-report reminder to prevent label drift in long reports. Define the tier vocabulary as a shared constant for C33.

## What exactly is changing?

### Existing baseline (what already works)

These are NOT new in C29 — they are the current state the plan builds on:

- `agent.py:914-916`: `synthesize_final()` already receives `findings` (full list of `SkepticFinding` objects)
- `synthesize.py:581-604`: already builds `<skeptic_findings>` XML block from findings
- `synthesize.py:596,604`: already says "Any finding rated [Critical Finding] MUST be explicitly addressed in your recommendations"
- `skeptic.py:34-39`: `_count_severity()` already counts `[Critical Finding]` occurrences

### What C29 adds on top of that baseline

| # | Item | Module(s) | What Changes | Est. Size |
|---|------|-----------|-------------|-----------|
| 29-1 | Extract critical finding texts | `skeptic.py` | New `extract_critical_findings(findings: list[SkepticFinding]) -> tuple[str, ...]` — parse `[Critical Finding]` markers from `checklist` text, extract the text that follows each marker (to end of line), deduplicate, return as tuple. Reuses the pattern from `_count_severity()` but extracts content, not just counts. | ~25 lines |
| 29-2 | Targeted critical findings block | `synthesize.py` | Inside `synthesize_final()`, after the existing `skeptic_block` construction (line 584), call `extract_critical_findings()` on the same `skeptic_findings` parameter. When critical findings exist: build a separate `<critical_findings>` XML block listing each finding with a number, and add a per-finding instruction: "For each numbered critical finding below, either (a) remove the disputed claim from the report, (b) mark it `[Disputed]` with a one-sentence reason, or (c) cite additional evidence that addresses it. Do not leave any critical finding unaddressed." No new parameter on `synthesize_final()` — derive from existing `skeptic_findings`. | ~30 lines |
| 29-3 | Snippet-quality gate (standard mode) | `agent.py` | In `_research_with_refinement()` (line ~997), before calling `refine_query()`: check snippet quality. If the average snippet length across pass1 results is < 50 chars (indicating thin/empty search results), skip `refine_query()` and call `extract_noun_phrases()` instead. This is a low-signal heuristic, not score-based — scores are unavailable at this point (computed later in `evaluate_sources()`). | ~15 lines |
| 29-4 | Summary-quality gate (deep mode) | `agent.py` | In `_research_deep()` (line ~1077), before calling `refine_query()`: check summary quality. Pass1 summaries already exist at this point (line 1070-1072). If the average summary length is < 100 chars, skip `refine_query()` and use noun-phrase fallback. Deep mode has richer signal than standard (full summaries vs snippets) but still no relevance scores. | ~15 lines |
| 29-5 | Noun-phrase fallback | `search.py` | New `extract_noun_phrases(query: str) -> str` — extract meaningful words from original query by filtering a prebuilt stopword frozenset, recombine as a simpler search query. Validate with `validate_query_list()`. Return original query if extraction produces nothing valid. No LLM call. | ~30 lines |
| 29-6 | Evidence-tier labeling prompt | `synthesize.py` | Add to `synthesize_report()` and `synthesize_final()` prompt instructions: label each factual claim with `[Documented]`, `[Inferred]`, `[Illustrative]`, or `[Speculative]`. Also add a **mid-report reminder** near the end of the `<instructions>` block: "Remember: every factual claim in this report must carry an evidence-tier label." This mitigates label drift in long reports. | ~25 lines |
| 29-7 | Evidence-tier vocabulary constant | New `evidence.py` | Define `EVIDENCE_TIERS: Final[tuple[str, ...]] = ("documented", "inference", "illustrative", "speculative")` in a shared module. This is vocabulary only — C33 will define its own `ClaimConfidence` data model without being constrained by this constant. The constant provides the canonical tier names so prompts and future parsers use the same strings. | ~10 lines |

**Total: ~150 lines across 4 modules (skeptic.py, agent.py, synthesize.py, search.py) + 1 new module (evidence.py)**

## What must not change?

- All 1040 existing tests pass
- Existing report format is backward compatible (new `[Disputed]` and tier markers are additive)
- Quick mode behavior unchanged (no skeptic, no quality gate on refinement)
- `SkepticFinding` dataclass interface unchanged
- `synthesize_final()` parameter list unchanged (critical findings derived internally from existing `skeptic_findings`)
- `refine_query()` interface unchanged (caller decides whether to call it)
- Existing skeptic prompts unchanged (enforcement reads existing output)
- Existing `<skeptic_findings>` XML block and general "address critical findings" instruction remain — the new `<critical_findings>` block adds targeted per-finding enforcement on top

## How will we know it worked?

### Acceptance Tests (EARS)

#### Skeptic Enforcement (29-1 through 29-2)
- WHEN skeptic output contains `[Critical Finding]` markers THE SYSTEM SHALL extract them as a deduplicated tuple of finding texts
- WHEN skeptic output contains no `[Critical Finding]` markers THE SYSTEM SHALL produce an empty tuple (no `<critical_findings>` block added)
- WHEN critical findings are extracted THE SYSTEM SHALL build a numbered `<critical_findings>` XML block inside `synthesize_final()` with per-finding enforcement instructions
- WHEN the `<critical_findings>` block is present THE SYSTEM SHALL instruct the model to address each numbered finding (remove, mark `[Disputed]`, or cite evidence)
- WHEN skeptic review fails (SkepticError caught at agent.py:906) THE SYSTEM SHALL produce no critical findings block (graceful degradation, existing behavior)
- WHEN mode is quick THE SYSTEM SHALL skip skeptic entirely (existing behavior, unchanged)

#### Snippet/Summary Quality Gate (29-3 through 29-5)
- WHEN standard mode pass1 average snippet length is < 50 chars THE SYSTEM SHALL skip `refine_query()` and use `extract_noun_phrases()` instead
- WHEN standard mode pass1 average snippet length is >= 50 chars THE SYSTEM SHALL proceed with `refine_query()` as normal
- WHEN deep mode pass1 average summary length is < 100 chars THE SYSTEM SHALL skip `refine_query()` and use `extract_noun_phrases()` instead
- WHEN deep mode pass1 average summary length is >= 100 chars THE SYSTEM SHALL proceed with `refine_query()` as normal
- WHEN noun-phrase extraction produces a valid query (passes `validate_query_list()`) THE SYSTEM SHALL use it for the refinement search
- WHEN noun-phrase extraction fails THE SYSTEM SHALL use the original query (safe fallback)
- WHEN mode is quick with decompose=False THE SYSTEM SHALL skip refinement entirely (existing behavior, unchanged)

#### Evidence-Tier Labeling (29-6 through 29-7)
- WHEN synthesizing any mode report THE SYSTEM SHALL include evidence-tier labeling instructions in the synthesis prompt
- WHEN the report synthesis instruction exceeds 1500 tokens THE SYSTEM SHALL include a mid-report tier-label reminder near the end of the instruction block
- WHEN `EVIDENCE_TIERS` is imported from `evidence.py` THE SYSTEM SHALL provide exactly four canonical tier names
- WHEN `synthesize_draft()` is called THE SYSTEM SHALL NOT include evidence-tier instructions (draft is objective, no tier labels)

### Verification Commands
- `python3 -m pytest tests/ -v` — all 1040+ tests pass
- `python3 -m pytest tests/test_skeptic.py -v -k critical` — new critical finding extraction tests
- `python3 -m pytest tests/test_synthesize.py -v -k tier` — new evidence-tier tests
- `python3 -m pytest tests/test_search.py -v -k noun_phrase` — new noun-phrase extraction tests

## What is the most likely way this plan is wrong?

1. **Skeptic output parsing is fragile.** The `[Critical Finding]` marker is LLM-produced text. `_count_severity()` already proves case-insensitive counting works, but extraction may need fuzzy matching for variants like `**Critical Finding**` (bold markdown). Mitigation: start with case-insensitive exact match, add fuzzy matching in review if needed.

2. **Snippet/summary quality thresholds may be wrong.** The 50-char (standard) and 100-char (deep) thresholds are heuristic. If Tavily consistently returns short but relevant snippets for certain query types, the gate could fire incorrectly and skip useful summary-based refinement. Mitigation: log when the gate fires so we can audit post-deployment. Thresholds are constants, easily tuned.

3. **Evidence-tier labels may drift in long reports despite the mid-report reminder.** The reminder is a lightweight mitigation, not an enforcement mechanism. C33 adds post-synthesis extraction and validation. If labels are consistently absent in deep mode reports during work-phase testing, escalate to review before shipping.

## Implementation Sessions

### Session 1: Skeptic Enforcement (~55 lines)

**Files:** `skeptic.py`, `synthesize.py`

1. Add `extract_critical_findings(findings: list[SkepticFinding]) -> tuple[str, ...]` to `skeptic.py`
   - Case-insensitive search for `[Critical Finding]` in each finding's `checklist`
   - Extract the text following each marker (to end of line)
   - Deduplicate by normalized text
   - Return as frozen tuple
2. In `synthesize_final()` (synthesize.py), after existing skeptic block construction (line ~584):
   - Import and call `extract_critical_findings(skeptic_findings)`
   - When non-empty: build numbered `<critical_findings>` XML block with `sanitize_content()`
   - Add per-finding enforcement instruction after existing `skeptic_instruction`
   - No new parameter — derive from existing `skeptic_findings` param

**Tests (~10):**
- Extract from skeptic output with 0, 1, 3 critical findings
- Case-insensitive matching
- Deduplication across lenses
- `synthesize_final()` prompt includes `<critical_findings>` when findings exist
- `synthesize_final()` prompt does NOT include block when no critical findings
- Existing `<skeptic_findings>` block still present (not replaced)

**Commit:** `feat(29-1): extract and enforce skeptic critical findings`

### Session 2: Quality Gate + Noun Phrases (~60 lines)

**Files:** `agent.py`, `search.py`

1. Add `extract_noun_phrases(query: str) -> str` to `search.py`
   - Prebuilt `STOPWORDS: frozenset[str]` (common English stopwords)
   - Filter query words through stopwords
   - Validate with `validate_query_list()`
   - Return original query if extraction produces nothing valid
2. In `_research_with_refinement()` (agent.py ~line 997):
   - Compute average snippet length from pass1 results
   - If avg < 50 chars: log "Snippet quality below threshold, using noun-phrase fallback", call `extract_noun_phrases()` instead of `refine_query()`
3. In `_research_deep()` (agent.py ~line 1077):
   - Compute average summary length from pass1 summaries (which exist at this point)
   - If avg < 100 chars: log "Summary quality below threshold, using noun-phrase fallback", call `extract_noun_phrases()` instead of `refine_query()`

**Tests (~8):**
- Noun-phrase extraction from various query formats
- Stopword removal
- Fallback to original query when extraction fails
- Standard mode: gate fires on short snippets, skips refine_query
- Standard mode: gate does not fire on normal snippets
- Deep mode: gate fires on short summaries
- Deep mode: gate does not fire on normal summaries

**Commit:** `feat(29-2): snippet/summary quality gate with noun-phrase fallback`

### Session 3: Evidence-Tier Labeling (~35 lines)

**Files:** new `evidence.py`, `synthesize.py`

1. Create `research_agent/evidence.py` with `EVIDENCE_TIERS` constant
   - Include a docstring: "Vocabulary only — canonical tier names for synthesis prompts and future C33 parsing. This does not define the C33 ClaimConfidence data model."
2. Add evidence-tier instruction block to `synthesize_report()` — append to `mode_instructions`
3. Add evidence-tier instruction block to `synthesize_final()` — append to synthesis instructions
4. Add mid-report reminder: "Remember: every factual claim must carry one of these evidence-tier labels: [Documented], [Inferred], [Illustrative], [Speculative]." placed near the end of the `<instructions>` block in both functions

**Tests (~6):**
- `EVIDENCE_TIERS` constant contains exactly 4 values
- Evidence-tier instruction appears in `synthesize_report()` prompt
- Evidence-tier instruction appears in `synthesize_final()` prompt
- Mid-report reminder appears in both prompts
- Tier instruction does NOT appear in `synthesize_draft()` prompt
- Labels are additive (don't break existing report format tests)

**Commit:** `feat(29-3): evidence-tier labeling with mid-report reminder`

### Session 4: Integration Testing (~10 lines test fixtures)

1. Run full test suite
2. Integration test: mock skeptic output with `[Critical Finding]`, verify numbered `<critical_findings>` block in synthesis prompt
3. Verify existing `<skeptic_findings>` block still present alongside new `<critical_findings>`
4. Verify evidence-tier instruction absent from `synthesize_draft()`

**Commit:** `test(29-4): integration tests for enforcement and evidence tiers`

## Dependencies & Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| `[Critical Finding]` parsing fragility | MEDIUM | Case-insensitive. Existing `_count_severity()` proves pattern. |
| Quality gate thresholds (50/100 chars) are heuristic | LOW | Log when gate fires. Constants easily tuned. |
| Evidence-tier labels drift in long reports | MEDIUM | Mid-report reminder instruction. Escalate if labels absent in deep-mode testing. |
| `extract_critical_findings()` import in `synthesize.py` adds cross-module dependency | LOW | `skeptic.py` → `synthesize.py` is a new import direction. Acceptable: skeptic output is already consumed by synthesize. |

## Feed-Forward

- **Hardest decision:** Whether to add a new `critical_findings` parameter to `synthesize_final()` or derive internally. Chose derive internally — the function already receives `skeptic_findings`, so extracting the critical subset inside the function keeps the interface unchanged and avoids pretending this is new threading.
- **Rejected alternatives:** (1) Real score-aware refinement using `evaluate_sources()` — scores are unavailable at refinement time in both standard and deep mode. Would require refactoring the entire pipeline or adding a pre-scoring LLM call. (2) Adding `critical_findings` as a new parameter — unnecessary indirection when `synthesize_final()` already has the data. (3) Deferring tier-drift mitigation entirely to C33 — Codex correctly flagged this as leaving the least-confident item unresolved.
- **Least confident:** Evidence-tier label consistency in long deep-mode reports (~3500 words). The mid-report reminder is a lightweight mitigation — if labels are consistently absent in later sections during work-phase testing, we need a stronger approach (e.g., per-section labeling instruction). This is the concrete verification gate: during Session 4, run one deep-mode test query and manually inspect whether labels appear in the final 3 sections.

## Three Questions

1. **Hardest decision in this session?** Reframing "score-aware refinement" as "quality gate." The entropy roadmap assumed scores were available; the code shows they aren't. Honest description of what the feature actually does (snippet/summary length heuristic) instead of what we wished it did (score-based gating).
2. **What did you consider changing but left alone, and why?** The `synthesize_final()` parameter list. Adding `critical_findings` as a parameter would make the interface look cleaner, but the function already receives the full `skeptic_findings` — adding a redundant subset parameter would make it look like the current integration doesn't exist. Deriving inside the function is more honest about the baseline.
3. **Least confident about going into work?** Tier-label drift in deep mode. The concrete entry gate: during Session 4 integration testing, generate one deep-mode report and check labels in the final 3 sections. If labels are absent in >50% of final sections, add a per-section reminder before shipping. If labels appear in >50%, the mid-report reminder is sufficient.

## Codex Work Review Handoff

```
Read these files first for project context:
  - HANDOFF.md
  - CLAUDE.md

Review branch main against docs/plans/2026-04-21-cycle-29-skeptic-enforcement-plan.md.

Focus on:
1. Does the diff match the plan? Flag anything added or missing.
2. Does extract_critical_findings() correctly parse the skeptic checklist
   format? Check against real skeptic output samples in tests.
3. Does the quality gate in standard mode (_research_with_refinement)
   use snippet length, and deep mode (_research_deep) use summary length?
   These must be different — deep mode has richer data.
4. Does the <critical_findings> block appear alongside (not replacing)
   the existing <skeptic_findings> block?
5. Does evidence-tier instruction appear in synthesize_report() and
   synthesize_final() but NOT synthesize_draft()?
6. Does the mid-report reminder appear in the instruction block?
7. Feed-Forward risk: did the work session verify tier labels in a
   deep-mode report's final sections?

Key files changed: skeptic.py, synthesize.py, agent.py, search.py, evidence.py
Plan doc: docs/plans/2026-04-21-cycle-29-skeptic-enforcement-plan.md

Output: findings ordered by severity + a Claude Code fix prompt.
```
