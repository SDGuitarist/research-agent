# Review Context — Research Agent

## Risk Chain

**Brainstorm risk:** "The snippet tier detection mechanism — how to set source_tier on Summary without text-prefix fragility."

**Plan mitigation:** Option (b) chosen: `source_tier` field on `ExtractedContent` with default `"full"`. Cascade sets `"snippet"` at creation time (point of knowledge). Threading through summarize follows established parameter-passing pattern.

**Work risk (from Feed-Forward):** "A/B test outcome — cutoff=4 may compound with Haiku borderline aggressiveness. Mitigation: 1-line revert per mode."

**Review resolution:** 0 P1, 3 P2, 5 P3 from 7 agents. All P2s fixed in commit `dd790ce`. Top findings: `chr(10)` readability (replaced with helper), ModeInfo missing relevance gate fields (added 3 fields), surviving sources outside XML boundary (wrapped in tags).

**Compound lesson:** MCP parity is the #1 recurring review finding (Cycles 19, 26, 27, 28). When adding `ResearchMode` fields, update `ModeInfo` + `list_modes()` + `list_research_modes` in the same commit. Also: wrap all LLM prompt content in XML boundary tags — defense-in-depth requires sanitize + XML + system prompt on every path.

## Files to Scrutinize

| File | What changed | Risk area |
|------|-------------|-----------|
| `research_agent/relevance.py` | SNIPPET_SCORE_CAP, score cap, surviving_sources, XML boundary, instruction list helper | Score cap must cover all exit paths; new prompt content needs XML boundaries |
| `research_agent/extract.py` | `SourceTier` type alias + `source_tier` field on `ExtractedContent` | New field with default — backward compatibility for 39 test constructors |
| `research_agent/summarize.py` | `source_tier` on `Summary`, threaded through `summarize_chunk`/`summarize_content` | 104 test constructors rely on default |
| `research_agent/modes.py` | `relevance_cutoff=4` (standard/deep), `min_sources_short_report=2` (quick) | Config-only changes — no logic changes needed |
| `research_agent/results.py` | 3 new fields on `ModeInfo` | MCP parity — must match `list_research_modes` output |
| `research_agent/mcp_server.py` | Gate info in `list_research_modes` output | Agent-facing output format |

## Deferred Items Tracking

| Item | Deferral Count | Rule |
|------|---------------|------|
| MCP `--cost` + `--critique-history` tools (#123) | 2 | Promoted to Cycle 31 (promote-or-drop applied) |
| MCP `test_mcp_server.py` verification | 1 | Missing fastmcp dependency — verify when installed |
| A/B live validation (cutoff 3 vs 4) | 1 | Blocked by expired API key — run `scripts/validate_cutoff_ab.py` when renewed |
| `_aggregate_by_source` exception-path cap bypass | 1 | No-op while SNIPPET_SCORE_CAP=3 — fix if cap lowered |

## Plan Reference

`docs/plans/2026-04-05-cycle-28-relevance-source-quality-plan.md`
Entropy roadmap (cycles 27-31): `docs/research/2026-03-09-entropy-fixes-roadmap.md`
