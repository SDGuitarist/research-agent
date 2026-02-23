# Handoff: Self-Enhancing Agent Review Fixes

## Current State

**Branch:** `main` (pushed)
**Phase:** Fix-batched (batches 1-6 complete, remaining P2s and P3s left)
**Tests:** 608 passing

## What's Done

All P1s and the high-priority P2s from the self-enhancing agent code review are fixed:

| Batch | Findings | Summary |
|-------|----------|---------|
| 1 | P1 #1-4 | Fix `except Exception`, add `--critique`/`--critique-history` CLI, print critique summary |
| 2 | P2 #5-9 | Extract `META_DIR`, remove dead `CritiqueError`, `asyncio.to_thread` wrapping, unify param names, XML tags |
| 3 | P2 #10-11 | Sanitize weakness strings, register critique in token budget |
| 4 | P2 #12 | Replace mutable `_critique_context` with parameter threading (#13 skipped — no longer dead) |
| 5 | P2 #14-15 | Add `critique` field to `ResearchResult`, replace thin tests with pipeline integration tests |
| 6 | P2 #16-18 | Fix filtering docstring confusion, add missing param docs, add `--no-critique` CLI flag |

## What's Left

**Remaining P2s (#19-23):** Process/documentation issues, not code fixes
- #19: Missing plan document in `docs/plans/` — document the gap
- #20: Commit size convention violated — process improvement for future
- #21: `query_domain` machinery is YAGNI — remove `domain` parameter from `load_critique_history`
- #22: Critique saved before report persisted — acceptable for CLI, note for future
- #23: Duplicated dimension constants — extract `CRITIQUE_DIMENSIONS` single source of truth

**P3s (#24-34):** Nice-to-haves (f-string in loggers, duplicate scores tuple, double sanitization, timestamp collision, bool bypass, quick mode loads history, redundant sanitize calls, critique threshold not configurable, survivorship bias, test quality, minor tidiness)

## Decision Point

The next session should decide:
1. **Fix remaining P2s (#21, #23)** — the two that are actual code changes (~30 min)
2. **Skip to compound phase** — document learnings from batches 1-6 in `docs/solutions/`
3. **Clean up P3s** — low-value but improves consistency

Recommendation: Fix #21 and #23 (the code-level P2s), skip #19-20 and #22 (process notes), then move to compound phase.

## Prior Phase Risk (from batch 6)

> "The `--no-critique` flag has no dedicated test. The existing `test_quick_mode_skips_critique` test covers the early-return path in `_run_critique`, and the `skip_critique` check uses the same code path. A test that constructs `ResearchAgent(skip_critique=True)` and verifies `_run_critique` returns early would be quick to add but wasn't in scope for this batch."

## Three Questions

1. **Hardest implementation decision in this session?** Finding #14 — whether to change `agent.research()` to return `ResearchResult` (breaking API) or add `critique` to the existing `ResearchResult` used by `run_research_async()` (non-breaking). Chose the non-breaking path since `last_critique` property already covers the CLI path.

2. **What did I consider changing but left alone, and why?** The `--no-critique` flag could also skip loading critique history, but history loading is cheap (YAML reads) and improves prompt quality. Only the expensive API call in `_run_critique` is skipped.

3. **Least confident about going into review?** The `--no-critique` flag lacks a dedicated test. It shares the early-return path with quick mode, which is tested, but a direct test would be better.
