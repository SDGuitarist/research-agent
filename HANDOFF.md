# HANDOFF — Research Agent

**Date:** 2026-04-05
**Branch:** `main`
**Phase:** Cycle 27 — Work, Session 2 COMPLETE. Ready for Session 3.

## Current State

Sessions 1-2 done. Session 1: idempotent sanitization. Session 2: vague query detection gate in `query_validation.py` + `VagueQueryError` in `errors.py` + pre-flight check in `agent.py:_research_async()`. 941 tests passing. Two existing tests updated (used single-word query "test" that now fails vague check). One brainstorm assumption corrected: "what's up" has 2 meaningful words ("what's" + "up"), not 0 — "up" is not a stop word.

## Key Artifacts

| Phase | Location |
|-------|----------|
| Brainstorm | `docs/brainstorms/2026-04-05-cycle-27-input-validation-brainstorm.md` |
| Plan | `docs/plans/2026-04-05-cycle-27-input-validation-plan.md` |
| Session 1 commit | `fix(27-1): make sanitize_content idempotent via unescape-then-escape` |
| Session 2 commit | `feat(27-2): add vague query detection gate` |

## Deferred Items

- **Tier 3 model routing** (summarization) — deferred indefinitely
- **IDN/punycode domain matching** — known limitation, acceptable
- **MCP `--cost` + `--critique-history` tools** (#123) — Cycle 31

## Three Questions

1. **Hardest implementation decision?** The "what's up" test case. Brainstorm assumed 0 meaningful words, but `meaningful_words()` returns {"what's", "up"} — "up" isn't a stop word. Fixed by changing the test to use pure stop words ("the and or") instead. Did not add "up" to STOP_WORDS — that would affect other valid uses.
2. **What did you consider changing but left alone?** Considered adding "up" to STOP_WORDS or expanding VAGUE_WORDS. Left alone — these changes would affect unrelated code paths (validate_query_list, decompose) and aren't worth the blast radius for one edge case.
3. **Least confident about going into review?** Existing tests that use short queries like `"test query"` all pass because they have 2 meaningful words. But any future test that uses a 1-word query will hit VagueQueryError unexpectedly. This is a new constraint that test authors need to know about.

### Prompt for Next Session

```
Read docs/plans/2026-04-05-cycle-27-input-validation-plan.md. Implement Session 3: Per-Task Temperature Controls. Relevant files: research_agent/modes.py, research_agent/results.py, research_agent/agent.py, research_agent/summarize.py, research_agent/skeptic.py, research_agent/synthesize.py, research_agent/relevance.py, research_agent/decompose.py, research_agent/context.py, research_agent/search.py, research_agent/coverage.py, research_agent/iterate.py, research_agent/critique.py. Do only Session 3 — commit and stop.
```
