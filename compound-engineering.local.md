# Review Context — Research Agent

## Risk Chain

**Brainstorm risk:** "Whether Haiku's decompose quality is good enough for complex multi-topic queries — sub-query generation for nuanced topics might produce less targeted queries, leading to weaker search results downstream."

**Plan mitigation:** Verification step — run 3-5 test queries comparing Haiku vs Sonnet decompose output before shipping. Work phase tackles decompose first so quality can be assessed early.

**Work risk (from Feed-Forward):** "Whether `identify_coverage_gaps()` on Haiku will correctly classify gap taxonomy types (QUERY_MISMATCH, THIN_FOOTPRINT, ABSENCE)."

**Review resolution:** 5 findings (0 P1, 3 P2, 2 P3) from 7 agents. All resolved. Top issues: ModeInfo missing planning_model (P2), redundant debug logs (P2), no integration test for routing (P2).

**Fix risk (from Three Questions):** "Whether the 2 integration tests are sufficient coverage — 5 other planning call sites remain untested but use identical pattern."

**Compound resolution:** Accepted risk — all 7 sites use identical `model=self.mode.planning_model` pattern. Documented monitoring guidance: first 10-20 real runs with `-v` to spot-check quality.

## Files to Scrutinize

| File | What changed | Risk area |
|------|-------------|-----------|
| `research_agent/modes.py` | Added `planning_model` field to frozen dataclass | New field must propagate to ModeInfo |
| `research_agent/agent.py` | 7 call sites changed to `self.mode.planning_model` + 1 summary debug log | Correct planning vs synthesis split |
| `research_agent/results.py` | Added `model` + `planning_model` to ModeInfo dataclass | ModeInfo/ResearchMode drift |
| `research_agent/mcp_server.py` | Updated `list_modes()` output + `run_research` docstring | Agent-native parity |

## Plan Reference

`docs/plans/2026-03-02-feat-tiered-model-routing-plan.md`
