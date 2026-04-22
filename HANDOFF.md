# HANDOFF — Research Agent

**Date:** 2026-04-21
**Branch:** `main`
**Phase:** Cycle 30 COMPLETE. Ready for Cycle 31 brainstorm.

## Current State

Cycle 30 shipped and compounded. Four features: source diversity gate (per-mode domain thresholds), cross-chunk context (sequential within source, prior summary threading), sentence-boundary truncation (tiered rfind fallback with percentage marker), synthesis abstention gate (single-source claim qualification). 1095 tests passing.

## Key Artifacts

| Phase | Location |
|-------|----------|
| Brainstorm | `docs/brainstorms/2026-04-21-cycle-30-summarization-context-preservation-brainstorm.md` |
| Plan | `docs/plans/2026-04-21-cycle-30-summarization-context-preservation-plan.md` |
| Solution | `docs/solutions/feature-implementation/summarization-context-preservation-diversity-truncation-abstention.md` |

## Deferred Items

- **ANTHROPIC_ERRORS consumption at 10+ call sites** — mechanical replacement for micro-cycle
- **MCP `--cost` + `--critique-history` tools** (#123) — Cycle 31
- **A/B live validation** — run `scripts/validate_cutoff_ab.py` when API keys renewed
- **Session 4 live tier-label validation (C29)** — run deep-mode query when API key replaced
- **One-sentence vs cumulative chunk summary** — if deep-mode chunk 3+ summaries show orphaned references, upgrade to cumulative
- **Diversity gate threshold tuning** — monitor short_report frequency for niche topics after API key renewal

## Three Questions

1. **Hardest decision?** Post-decision downgrade design for the diversity gate. Placing the check AFTER `compute_gate_decision()` means existing gate logic is untouched — non-obvious, corrected during plan deepening.
2. **What was rejected?** Regex for sentence truncation (rfind is simpler), `[Uncorroborated]` label (phrasing avoids parser debt), subdomain normalization (different editorial contexts).
3. **Least confident about?** Whether diversity gate + relevance cutoff combined effect causes too many short_report downgrades for niche queries. Untested end-to-end.

## Prompt for Next Session

```
Read HANDOFF.md for context. This is research-agent, a Python CLI research agent
that searches the web, fetches pages, and generates structured markdown reports
with citations using Claude.
Cycle 30 complete. Next: Cycle 31 brainstorm (novelty-biased decomposition +
MCP --cost and --critique-history tools).
See docs/research/2026-03-09-entropy-fixes-roadmap.md for C31 scope.
Start with /compound-start to load lessons and kick off.
```
