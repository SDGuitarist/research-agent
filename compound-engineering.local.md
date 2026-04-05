# Review Context — Research Agent

## Risk Chain

**Brainstorm risk:** "The vague word set heuristic misses subtler vague queries like 'tell me about technology' (2 meaningful words, neither in vague set, but still too broad)."

**Plan mitigation:** Accepted limitation. Documented exact boundary. Ship heuristic, monitor false negatives, tighten later. No LLM-based fallback in this cycle.

**Work risk (from Feed-Forward):** "The 3-deep wrapper chains for summarization and skeptic — existing tests mocking at intermediate boundaries may need mock call expectations updated for new `temperature` param."

**Review resolution:** 5 findings (0 P1, 3 P2, 2 P3) from 7 agents. All fixed in one commit. Top finding: `generate_insufficient_data_response` used planning_temperature (0.2) for user-facing prose — reclassified to summarize_temperature (0.5). The wrapper chain risk was a non-issue: `temperature: float = 1.0` defaults meant all existing mocks survived unchanged.

**Compound lesson:** Temperature task-type classification requires judgment — 15 of 16 call sites were obvious, but the ambiguous one was caught only by review. When classifying, consider output format, not logical decision. Also: MCP parity gaps are the most common review finding — always check standalone MCP tools when adding pipeline config.

## Files to Scrutinize

| File | What changed | Risk area |
|------|-------------|-----------|
| `research_agent/sanitize.py` | `html.unescape()` before escaping — idempotent now | Prompt injection defense layer — any regression breaks XML boundaries |
| `research_agent/query_validation.py` | `check_query_vagueness()` + `VAGUE_WORDS` frozenset | False positives could block legitimate queries |
| `research_agent/modes.py` | 3 temperature fields + validation on frozen `ResearchMode` | New fields need `ModeInfo` + `list_modes()` + MCP parity |
| `research_agent/agent.py` | 16 call sites pass `self.mode.*_temperature` | Missing temperature at a new call site defaults to 1.0 silently |
| `research_agent/mcp_server.py` | Temperature defaults on standalone tools, vague query hint, mode listing | MCP boundary is the most common place for parity gaps |
| `tests/test_sanitize.py` | 4 prompt injection regression tests | Named/numeric/hex/mixed entity boundary breakout |

## Deferred Items Tracking

| Item | Deferral Count | Rule |
|------|---------------|------|
| MCP `--cost` + `--critique-history` tools (#123) | 2 | Promoted to Cycle 31 (promote-or-drop applied) |
| MCP `test_mcp_server.py` verification | 1 | Missing fastmcp dependency — verify when installed |

## Plan Reference

`docs/plans/2026-04-05-cycle-27-input-validation-plan.md`
Entropy roadmap (cycles 27-31): `docs/research/2026-03-09-entropy-fixes-roadmap.md`
