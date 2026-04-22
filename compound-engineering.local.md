# Review Context — Research Agent

## Risk Chain

**Brainstorm risk:** Search coverage dependency — epistemic rigor sits on Tavily + DDG. C33 plan must decide: include "coverage confidence" or accept as structural risk.

**Plan mitigation:** Reframed "score-aware refinement" as "quality gate" since scores aren't available at refinement time. Added snippet/summary length heuristic instead.

**Work risk (from Feed-Forward):** Evidence-tier label consistency in long deep-mode reports (~3500 words). Mid-report reminder is lightweight mitigation. Regex parsing of [Critical Finding] is coincidental correctness (substring match).

**Review resolution:** 3 findings from Codex review. (1) Weak enforcement wording → strengthened to three-way contract. (2) Missing real-format regression tests → added 3 tests using actual skeptic output shapes. (3) Live validation gap → documented as deferred with unblock condition.

## Files to Scrutinize

| File | What changed | Risk area |
|------|-------------|-----------|
| `skeptic.py` | `extract_critical_findings()` + regex | Regex coincidental correctness — substring match for `[Critical Finding]` |
| `synthesize.py` | `<critical_findings>` block + evidence-tier instructions + mid-report reminder | Token budget (~200 tokens unregistered), tier-label drift in deep mode |
| `agent.py` | Quality gates in `_research_with_refinement` and `_research_deep` | Cascading effect: noun-phrase fallback → simpler query → fewer pass2 results → more insufficient_data |
| `search.py` | `extract_noun_phrases()` | Reuses `STOP_WORDS` from query_validation — adequate for fallback but not comprehensive |
| `evidence.py` | New module — tier constants and prompt text | Single source of truth for label vocabulary |

## Plan Reference

`docs/plans/2026-04-21-cycle-29-skeptic-enforcement-plan.md`
