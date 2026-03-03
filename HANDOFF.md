# HANDOFF — Research Agent

**Date:** 2026-03-03
**Branch:** `main`
**Phase:** Cycle 21 fix phase complete — ready for compound phase
**Last commit:** `5ee8d9a` — docs(21): update model comment and MCP docstring for tiered routing

## What Was Done This Session

1. **Fixed all 5 review findings** from Cycle 21 in recommended order:

| # | Issue | Commit | What Changed |
|---|-------|--------|-------------|
| 116 | ModeInfo agent visibility | `8d93bcc` | Added `model` + `planning_model` fields to ModeInfo, list_modes(), MCP output |
| 114 | Consolidate debug logs | `059404f` | Replaced 7 per-call-site frozen-value logs with 1 summary log (-6 net LOC) |
| 115 | Integration test for routing | `9ac1f04` | Added 2 tests: decompose_query + refine_query receive AUTO_DETECT_MODEL |
| 117 | Model field comment | `5ee8d9a` | Updated "for all API calls" → "for synthesis and quality-critical calls" |
| 118 | MCP docstring | `5ee8d9a` | Added tiered routing note to run_research docstring |

2. **All 874 tests pass** (872 existing + 2 new from fix 115)
3. **Marked all 5 todo files as done** (status: pending → done)

## Deferred Items

From prior cycles (unchanged):
- Tier 2: Haiku for relevance scoring (needs A/B comparison data)
- Tier 3: Haiku for summarization (deferred indefinitely — too risky)
- `validate_query_list()` on `refine_query()` output (pre-existing gap, low priority)
- Standalone `generate_followups` MCP tool (agent-native parity)
- `iteration_sections: tuple[str, ...]` structured field on ResearchResult
- Per-query source count observability
- Double-sanitization idempotency risk (standing risk from Cycle 20)
- Update `cost_estimate` strings after real usage data collected
- Monitor Haiku decompose quality on first 10-20 real runs (feed-forward from review)

## Three Questions (Fix-Batched Phase)

1. **Hardest fix in this batch?** Fix 115 (integration test) — needed to find the right mock setup to exercise the standard mode pipeline through decompose_query while avoiding the existing test's patterns that don't mock decompose. Also caught a wrong field name (`classification` vs `is_complex`) in `DecompositionResult`.

2. **What did you consider fixing differently, and why didn't you?** For fix 116, considered Option B (adding a `to_mode_info()` method on ResearchMode to auto-generate ModeInfo and prevent future drift). Chose Option A (manual 2-field addition) because the fix scope was "add model visibility" not "refactor ModeInfo construction" — YAGNI for a fix phase.

3. **Least confident about going into compound phase?** Whether the 2 integration tests in fix 115 are sufficient coverage. They test decompose_query (standard mode) and refine_query (quick mode), but 5 other planning call sites (identify_coverage_gaps, generate_refined_queries, generate_followup_questions, evaluate_report, and the deep-mode refine_query) remain untested. A regression at those sites wouldn't be caught. However, all 7 sites use the identical `model=self.mode.planning_model` pattern, so a regression would likely hit the tested sites too.

## Next Phase

**Compound** — document what was solved in `docs/solutions/`, then `/update-learnings`.

### Prompt for Next Session

```
Read HANDOFF.md. Run /workflows:compound for Cycle 21. The cycle added tiered model routing (planning steps use Haiku, synthesis stays on Sonnet) and fixed 5 review findings. Key files: research_agent/modes.py, research_agent/agent.py, research_agent/results.py, research_agent/mcp_server.py. See docs/reviews/cycle-21/REVIEW-SUMMARY.md for the full review context.
```
