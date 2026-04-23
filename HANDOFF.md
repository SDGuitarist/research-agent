# HANDOFF — Research Agent

**Date:** 2026-04-23
**Branch:** `feat/31-novelty-decomposition-mcp-critique`
**Phase:** Cycle 31 COMPLETE. Entropy roadmap (C27-C31) fully shipped.

## Current State

Cycle 31 shipped novelty-biased decomposition (`novelty_queries` field on ResearchMode, conditional system prompt append in decompose.py) and MCP `get_critique_history` tool. Review found 0 P1, 4 P2, 2 P3 — all resolved. The entropy roadmap (5 cycles, 15 items) is now complete. 1118 tests passing, MCP lint 8/8.

## Key Artifacts

| Phase | Location |
|-------|----------|
| Brainstorm | `docs/brainstorms/2026-04-22-cycle-31-novelty-decomposition-mcp-tools-brainstorm.md` |
| Plan | `docs/plans/2026-04-23-feat-novelty-decomposition-mcp-cost-critique-plan.md` |
| Codex Handoff | `docs/plans/2026-04-23-codex-plan-review-handoff.md` |
| Solution | `docs/solutions/feature-implementation/novelty-decomposition-mcp-critique-history.md` |

## Deferred Items

- **ANTHROPIC_ERRORS consumption at 10+ call sites** — mechanical replacement for micro-cycle
- **A/B live validation of novelty decomposition** — run when API keys renewed
- **Diversity gate threshold tuning** — monitor SHORT_REPORT frequency after novelty is live
- **`META_DIR` promotion to public location** — 3 consumers, accepted as existing pattern
- **`to_mode_info()` method on ResearchMode** — eliminates manual 6-file sync

## Three Questions

1. **Hardest pattern to extract?** "MCP parity means side effects too" — the critique_report gap was pre-existing but only visible because get_critique_history created the feedback loop.
2. **What was left out?** The TOCTOU symlink gap in critique file loading — pre-existing infrastructure concern, not related to C31 features.
3. **Least confident about?** Whether novelty-framed sub-queries interact badly with the C30 diversity gate in practice. Architectural safety nets are in place but live A/B testing is needed.

## Prompt for Next Session

```
Read HANDOFF.md for context. This is research-agent, a Python CLI research agent
that searches the web, fetches pages, and generates structured markdown reports
with citations using Claude.
Cycle 31 complete. Entropy roadmap (C27-C31) fully shipped. Branch ready to merge.
Decide next: merge to main, or plan next cycle.
Start with /compound-start to load lessons and kick off.
```
