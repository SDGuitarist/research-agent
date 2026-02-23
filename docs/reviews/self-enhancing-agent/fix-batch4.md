# Fix Batch 4: P2 Findings #12 (skip #13)

**Commit:** `fix(critique): replace mutable _critique_context with parameter (#12)`
**Files changed:** `research_agent/agent.py`, `tests/test_critique.py`
**Tests:** 605 passed

## Prior Phase Risk

> "The generic `elif name in components` truncation handler in `_apply_budget_pruning` could silently truncate sources/business_context if they somehow fall through to it (they're handled by earlier if/elif branches, so this shouldn't happen). But the fallthrough path exists and has no test specifically verifying it doesn't fire for those two components."

Accepted: The if/elif chain is deterministic — `sources` and `business_context` always match their explicit branches before reaching the generic handler. The risk is low enough to accept without a dedicated test.

## Fixes Applied

### P2 #12: `_critique_context` as Mutable Instance State (agent.py:71)
- Removed `self._critique_context` from `__init__` and `_research_async`
- Created local `critique_context` variable in `_research_async`
- Threaded it as a parameter through the call chain:
  - `_research_async` → `_research_with_refinement` / `_research_deep`
  - Both → `_evaluate_and_synthesize`
  - `_evaluate_and_synthesize` → `evaluate_sources` and `synthesize_final`
- Eliminates state leak if `ResearchAgent` is reused across multiple `research()` calls
- Rewrote `TestAgentCritiqueHistoryThreading` → `TestCritiqueContextExtraction` to test ContextResult extraction without relying on instance state

### P2 #13: Skipped — No Longer Dead Code
- `_last_critique` IS read by production code: `cli.py:305` uses `agent.last_critique` for the critique summary output (added in batch 1, P1 #3)
- The review was written before batch 1 fixed the visibility issue — the finding is now moot
- `last_critique` property (lines 78-81) stays as-is

## Three Questions

1. **Hardest fix in this batch?** Threading `critique_context` through three method signatures (`_research_with_refinement`, `_research_deep`, `_evaluate_and_synthesize`) without missing a call site. Verified with `grep _critique_context` showing zero remaining references.

2. **What did I consider fixing differently, and why didn't I?** Considered keeping `_critique_context` as instance state but resetting it in `_research_async` (which it already did). But the review correctly identifies that local variables are safer — other context values like `refined_query` are already local. Consistency and safety win over fewer parameters.

3. **Least confident about going into the next batch or compound phase?** The rewritten `TestCritiqueContextExtraction` tests are thin — they test ContextResult's truthiness, not that `_research_async` actually threads critique_context through to `evaluate_sources`/`synthesize_final`. Finding #15 (test reimplementation) would address this properly, but that's a later batch.
