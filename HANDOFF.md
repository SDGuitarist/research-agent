# HANDOFF — Research Agent

**Date:** 2026-05-03
**Branch:** `chore/32-hygiene-bundle` (merged to main)
**Phase:** Cycle 32 COMPLETE. Project PARKED -- resume when Tavily API key is renewed.

## Current State

Cycle 32 shipped three mechanical hygiene refactors:

1. **META_DIR to report_store.py** — moved from agent.py to sit next to REPORTS_DIR, following the existing "constant lives with its owning module" pattern. 4 import sites updated. mcp_server.py lazy imports now avoid loading the heavy agent.py orchestrator for path constants.

2. **to_mode_info() on ResearchMode** — explicit field mapping method eliminates 18-line manual ModeInfo construction in list_modes(). TypeError on missing required fields. Guard comment in results.py prevents circular imports. 3 new tests using dataclasses.fields() for auto-detection of field drift.

3. **ANTHROPIC_ERRORS adoption** — replaced inline exception tuples at 10 call sites across 9 files with the shared constant from errors.py. Left skeptic.py, synthesize.py (per-type logging), and agent.py:1125 (mixed tuple, can't unpack in except clause) untouched.

1121 tests passing, MCP lint 8/8.

## Key Artifacts

| Phase | Location |
|-------|----------|
| Brainstorm | `docs/brainstorms/2026-05-03-cycle-32-hygiene-bundle-brainstorm.md` |
| Plan | `docs/plans/2026-05-03-cycle-32-hygiene-bundle-plan.md` |
| Review | `docs/reviews/2026-05-03-cycle-32-review-summary.md` |
| Solution | `docs/solutions/architecture/constant-consolidation-and-dataclass-conversion.md` |

## Commits

| # | Message | Files |
|---|---------|-------|
| 1 | `refactor(32-1): move META_DIR from agent.py to report_store.py` | 4 |
| 2 | `refactor(32-2): add to_mode_info() on ResearchMode, simplify list_modes()` | 4 |
| 3 | `refactor(32-3): adopt ANTHROPIC_ERRORS at 10 call sites across 9 files` | 10 |

## Deferred Items

- **A/B live validation of novelty decomposition** — blocked on API key renewal
- **Diversity gate threshold tuning** — needs A/B data first
- **ModeInfo __post_init__ validation** — patterns reviewer flagged it as the only frozen dataclass without validation. Low priority.
- **converters.py extraction** — if modes.py -> results.py import edge causes problems in future cycles

## Three Questions

1. **Hardest implementation decision in this session?** The relevance.py dual-import. It needs both individual anthropic imports (for per-type catches at line ~280) AND ANTHROPIC_ERRORS (for the grouped catch at line ~574). Solved with a clarifying comment above the import block.
2. **What did you consider changing but left alone, and why?** agent.py:1125's mixed (ResearchError, APIError, ...) catch. Python doesn't support tuple unpacking in except clauses. Considered a module-level RESEARCH_AND_API_ERRORS constant but it's YAGNI for one site. Added a comment instead.
3. **Least confident about going into review?** Whether the modes.py -> results.py import edge will be flagged as a concern. The guard comment in results.py and the dataclasses.fields() test mitigate drift, but the dependency direction (internal config -> public API type) is architecturally unusual.

### Prompt for Next Session

```
Read docs/plans/2026-05-03-cycle-32-hygiene-bundle-plan.md. Review branch chore/32-hygiene-bundle (3 commits). Relevant files: report_store.py, modes.py, results.py, api_helpers.py, relevance.py, agent.py.
```
