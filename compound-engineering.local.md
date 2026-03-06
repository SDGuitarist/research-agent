# Review Context — Research Agent

## Risk Chain

**Brainstorm risk:** "Whether Haiku's decompose quality is good enough for complex multi-topic queries — sub-query generation for nuanced topics might produce less targeted queries, leading to weaker search results downstream."

**Plan mitigation:** Verification step — run 3-5 test queries comparing Haiku vs Sonnet decompose output before shipping. Work phase tackles decompose first so quality can be assessed early.

**Work risk (from Feed-Forward):** "Whether `identify_coverage_gaps()` on Haiku will correctly classify gap taxonomy types (QUERY_MISMATCH, THIN_FOOTPRINT, ABSENCE)."

**Review resolution:** 5 findings (0 P1, 3 P2, 2 P3) from 7 agents. All resolved. Top issues: ModeInfo missing planning_model (P2), redundant debug logs (P2), no integration test for routing (P2).

**Tier 2 A/B test risk:** "The zoning query dropped from 12→7 sources with Haiku scoring, worth monitoring borderline aggressiveness."

**Tier 2 resolution:** 9 queries A/B tested. Zero decision flips. Source count differences attributed to search variability, not scoring divergence. `relevance_model` promoted to permanent field.

**Compound lesson:** Compare decisions (gate outcomes), not raw metrics. Two-step promotion (env var → permanent field) validated as safe methodology. Fix measurement bugs before A/B testing.

## Files to Scrutinize

| File | What changed | Risk area |
|------|-------------|-----------|
| `research_agent/modes.py` | Added `planning_model` + `relevance_model` fields to frozen dataclass | New fields must propagate to ModeInfo |
| `research_agent/agent.py` | 7 call sites changed to `self.mode.planning_model` + 1 summary debug log | Correct planning vs synthesis split |
| `research_agent/relevance.py` | `evaluate_sources()` now routes to `mode.relevance_model` | Haiku borderline aggressiveness on scoring |
| `research_agent/results.py` | Added `model` + `planning_model` + `relevance_model` to ModeInfo | ModeInfo/ResearchMode drift |
| `research_agent/query_validation.py` | `meaningful_words()` strips punctuation + splits hyphens | Validation correctness for complex queries |

## Plan Reference

`docs/plans/2026-03-02-feat-tiered-model-routing-plan.md`
