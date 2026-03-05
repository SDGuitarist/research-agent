# Review Summary — Cycle 21: Tiered Model Routing

**Review Target:** Commit 435dd2e — `feat(21): add tiered model routing for planning steps`
**Branch:** `main`
**Date:** 2026-03-03

## Prior Phase Risk

> "Whether the 7 call sites are the complete and correct set. The grep shows 13 remaining `self.mode.model` references (8 synthesis call sites + 5 logger/step messages), which matches the plan's 'stays on Sonnet' table. But `evaluate_sources()` in `relevance.py` accesses `mode.model` internally — it's intentionally staying on Sonnet, but a reviewer might flag it."

**Resolution:** All agents confirmed the 7 call sites are correct and complete. The Python reviewer manually verified all 13 remaining `self.mode.model` references — all are synthesis/quality-critical calls that correctly stay on Sonnet. The `evaluate_sources()` pattern in `relevance.py` was reviewed by 3 agents (Python, Performance, Architecture) and unanimously classified as a documented, intentional exception, not a leak. The architecture reviewer confirmed the orchestrator-controls-routing pattern holds for 19/20 call sites with this single documented deviation.

## Findings Summary

- **Total Findings:** 5
- **P1 (CRITICAL):** 0
- **P2 (IMPORTANT):** 3 — Should Fix
- **P3 (NICE-TO-HAVE):** 2 — Enhancements

**Verdict: PASS — Ship it.** All 7 agents agree the commit is clean, well-scoped, and follows established patterns. No security, performance, or architectural concerns block merge.

### Recommended Fix Order

| # | Issue | Priority | Why this order | Unblocks |
|---|-------|----------|---------------|----------|
| 1 | 116 - Add planning_model to ModeInfo | P2 | Root cause of agent visibility gap; enables accurate docstring | 118 |
| 2 | 114 - Consolidate 7 debug logs to 1 | P2 | Independent, reduces noise, -6 LOC | — |
| 3 | 115 - Integration test for model routing | P2 | Independent, prevents regression | — |
| 4 | 117 - Update model field comment | P3 | Independent, 1-line fix | — |
| 5 | 118 - Update MCP docstring for tiered routing | P3 | Depends on 116 (ModeInfo change) | — |

### Known Patterns (from learnings-researcher)

- Change follows Model String Unification pattern (`docs/solutions/architecture/model-string-unification.md`) exactly
- Debug logging placement matches Parallel Async Synthesis patterns (`docs/solutions/architecture/parallel-async-synthesis-with-safety-barriers.md`)
- No deviations from established precedent

### Pre-existing Issues Noted (NOT introduced by this commit)

- `refine_query()` lacks `validate_query_list()` output validation — already tracked in HANDOFF.md deferred items; marginally more relevant with Haiku routing
- `evaluate_sources()` reads `mode.model` directly instead of receiving it as kwarg — documented architectural exception, clear Tier 2 refactoring path exists

## Created Todo Files

**P2 — Important:**
- `114-pending-p2-consolidate-debug-log-lines.md` — Replace 7 identical frozen-value debug logs with 1 summary log at run start
- `115-pending-p2-integration-test-planning-model-routing.md` — Add test asserting planning functions receive `model=AUTO_DETECT_MODEL`
- `116-pending-p2-modeinfo-planning-model-visibility.md` — Add `model` + `planning_model` fields to ModeInfo for agent visibility

**P3 — Nice-to-Have:**
- `117-pending-p3-model-field-comment-accuracy.md` — Update misleading "for all API calls" comment on `model` field
- `118-pending-p3-mcp-docstring-tiered-routing.md` — Add tiered routing mention to `run_research` MCP docstring

## Review Agents Used

1. **kieran-python-reviewer** — Pythonic patterns, type safety, test coverage
2. **security-sentinel** — Attack surface, prompt injection, model validation
3. **performance-oracle** — Latency, cost, quality degradation risk
4. **architecture-strategist** — Pattern compliance, abstraction level, naming
5. **code-simplicity-reviewer** — YAGNI, unnecessary complexity
6. **agent-native-reviewer** — MCP parity, agent visibility
7. **learnings-researcher** — Past solutions, institutional patterns

## Key Findings by Agent

### Python Reviewer: PASS
- All 7 call sites verified correct; all 13 remaining `self.mode.model` refs verified appropriate
- Coverage gap: no integration test for model kwarg routing (O1)
- Redundant adjacent logs before asyncio.gather (O2)
- Misleading `model` field comment (O3)

### Security Sentinel: PASS (P3s only)
- No new attack surfaces introduced
- Three-layer prompt injection defense is architecture-dependent, not model-dependent
- All 7 call sites have code-level output validation with safe defaults
- `planning_model` field is code-controlled only (frozen dataclass + factory methods)

### Performance Oracle: PASS
- 4-7% cost savings and 3-5s latency claims are reasonable/conservative
- No retry amplification risk — all failure paths have safe defaults, no retry loops
- No cascading failure paths — synthesis/quality calls remain on Sonnet
- Debug log overhead: ~350-700ns total per run (negligible)

### Architecture Strategist: PASS
- Single field is correctly sized for Tier 1 (dict mapping would be premature)
- Orchestrator-controls-routing pattern holds for 19/20 call sites
- `planning_model` naming is adequate (covers 5/7 precisely, 2/7 approximately)
- Default AUTO_DETECT_MODEL is appropriate for all three modes
- SOLID principles upheld across the board

### Code Simplicity Reviewer: MINOR TWEAKS
- Core change (1 field + 7 kwarg swaps) is already minimal
- 7 debug logs are YAGNI — replace with 1 summary log (-6 net LOC)
- Test assertions are fine, follow existing conventions

### Agent-Native Reviewer: NEEDS MINOR WORK
- `planning_model` invisible in `list_research_modes` output (ModeInfo gap)
- No asymmetric CLI/MCP gap (neither surface can override planning_model)
- MCP docstring doesn't mention tiered routing

### Learnings Researcher: CONFIRMED
- 4 relevant past solutions found, all support the approach
- Model String Unification pattern followed exactly
- No additional gaps detected

## Three Questions (Review Phase)

1. **Hardest judgment call in this review?** Whether the ModeInfo visibility gap (116) should be P2 or P3. Chose P2 because agent-native parity is an established project principle (Cycle 19), and this is the first time a new ResearchMode field was added without updating ModeInfo — setting the precedent that it's "acceptable to skip" would compound over future cycles.

2. **What did you consider flagging but chose not to, and why?** The `evaluate_sources()` pattern in `relevance.py` reading `mode.model` directly. Three agents independently reviewed it and all concluded it's a documented, intentional exception with a clear Tier 2 refactoring path. Creating a todo for it would duplicate the existing plan documentation and add noise.

3. **What might this review have missed?** Whether Haiku's decompose quality is actually sufficient for complex multi-topic queries in production. All agents noted this as the highest-risk call site but none could evaluate it without real usage data. The performance oracle recommends monitoring the first 10-20 runs with `-v` to spot-check decompose output quality. This is the feed-forward risk for the fix/compound phase.

## Feed-Forward

- **Hardest decision:** ModeInfo visibility as P2 vs P3 (see Three Questions)
- **Rejected alternatives:** Flagging `evaluate_sources` pattern as a todo (redundant with existing plan docs)
- **Least confident:** Whether Haiku decompose quality holds on complex queries — needs real run monitoring before Tier 2 decisions
