# Review Context — Research Agent

## Risk Chain

**Brainstorm risk:** Diversity gate + C28 relevance cutoff interaction may increase short_report frequency for niche topics with few authoritative sources.

**Plan mitigation:** Post-decision downgrade design — diversity check only tightens FULL_REPORT → SHORT_REPORT, never further. Thresholds (2/3/4) are constants easily tuned.

**Work risk (from Feed-Forward):** One-sentence prior-chunk summary may not provide enough context for 5+ chunk deep-mode sources. Sequential chunk processing adds ~20s worst case.

**Review resolution:** 3 findings from Codex. (1) MCP parity — `min_domains=` missing from list_research_modes. (2) Chunk position header missing — plan said "chunk index and total" but implementation only had prior summary. (3) No retry path regression test. All fixed.

## Files to Scrutinize

| File | What changed | Risk area |
|------|-------------|-----------|
| `relevance.py` | `check_domain_diversity()` + post-decision downgrade in `evaluate_sources()` | Gate only fires on FULL_REPORT — verify no path bypasses the guard |
| `summarize.py` | Sequential loop, `_extract_prior_context()`, chunk_index/total_chunks params | Concurrency model changed — semaphore still limits global, but within-source is sequential |
| `token_budget.py` | Tiered rfind() truncation + percentage marker | Abbreviation edge case ("Dr. Smith") — low risk, falls back to char-level |
| `synthesize.py` | ABSTENTION_INSTRUCTION injected in report + final, not draft | Instruction density in synthesize_final() now 8+ blocks |
| `agent.py` | Diversity check in `_try_coverage_retry()` | Same guard as evaluate_sources — must stay in sync |
| `mcp_server.py` | `min_domains=` in gate_info output | MCP parity fix from review |

## Plan Reference

`docs/plans/2026-04-21-cycle-30-summarization-context-preservation-plan.md`
