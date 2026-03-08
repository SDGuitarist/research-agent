# Review Context — Research Agent

## Risk Chain

**Brainstorm risk:** "How `preferred_domains` scoring boost integrates with `evaluate_sources()` — the boost needs to happen post-LLM-scoring without distorting the gate decisions."

**Plan mitigation:** Removed `preferred_domains` entirely (YAGNI — +0.5 boost is a no-op on int scores with int cutoff). Consolidated blocked_domains to single-funnel filter in `_fetch_extract_summarize()`.

**Work risk (from Feed-Forward):** "Per-field try/except structure in `_parse_template()` — verify that a malformed `blocked_domains` field truly does NOT prevent `synthesis_tone` from parsing."

**Review resolution:** 4 findings (0 P1, 2 P2, 2 P3). Top finding: blocked domains leak into `refine_query()` inputs before reaching the single-funnel filter. All 4 resolved with 18 new tests.

**Compound lesson:** Single-funnel filtering is necessary but not sufficient — trace ALL upstream consumers of unfiltered data. Document "already sanitized" at consumption sites, not just the sanitization site.

## Files to Scrutinize

| File | What changed | Risk area |
|------|-------------|-----------|
| `research_agent/context_result.py` | New `ContextProfile` frozen dataclass | Carries on `ContextResult` — any new field needs default |
| `research_agent/context.py` | Per-field profile parsing in `_parse_template()` | Nested try/except complexity, sanitize-once boundary |
| `research_agent/search.py` | `filter_blocked_urls()` with dot-boundary matching | Domain matching edge cases (IDN/punycode bypass known) |
| `research_agent/agent.py` | Early filter + funnel filter, gap_schema fallback, tone threading | `self.schema_path` must be set by fallback path |
| `research_agent/synthesize.py` | `TONE_PRESETS`, `_build_tone_instruction()`, tone params | Tone tag OUTSIDE `<instructions>` block |
| `research_agent/cli.py` | `--list-contexts` with `_parse_template` private import | Coupling to private function |

## Cross-Tool Review Protocol

Codex is an independent second-opinion agent in this workflow. For reviews:
1. Run Codex `review-branch-risks` first (independent findings)
2. Then run Claude Code `/workflows:review` (compound review with learnings researcher)
3. Merge both finding sets, deduplicate, and apply fix ordering per CLAUDE.md rules

## Plan Reference

`docs/plans/2026-03-06-feat-swappable-context-profiles-plan.md`
