# Fix Batch 5: P2 Findings #14-15

**Commit:** `fix(critique): add CritiqueResult to ResearchResult, fix test reimplementation (#14-15)`
**Files changed:** `research_agent/results.py`, `research_agent/__init__.py`, `tests/test_critique.py`, `tests/test_public_api.py`, `tests/test_results.py`
**Tests:** 608 passed

## Prior Phase Risk

> "The rewritten `TestCritiqueContextExtraction` tests are thin — they test ContextResult's truthiness, not that `_research_async` actually threads critique_context through to `evaluate_sources`/`synthesize_final`. Finding #15 (test reimplementation) would address this properly, but that's a later batch."

Addressed: Replaced thin tests with `TestCritiqueContextThreading` that mocks the pipeline and asserts `critique_guidance` actually arrives at `evaluate_sources` and `synthesize_final`.

## Fixes Applied

### P2 #14: CritiqueResult Not in `research()` Return Value
- Added `critique: CritiqueResult | None = None` field to `ResearchResult` in `results.py`
- Used `TYPE_CHECKING` import to avoid circular import between `results.py` and `critique.py`
- Updated `run_research_async()` in `__init__.py` to populate `critique=agent.last_critique`
- Programmatic consumers now get critique data in the return value without accessing private state
- CLI path unchanged — still uses `agent.last_critique` property (added in batch 1)

### P2 #15: Tests Reimplement Agent Logic Instead of Testing It
- Replaced `TestCritiqueContextExtraction` (2 tests that only tested `ContextResult` truthiness) with `TestCritiqueContextThreading` (3 async integration tests)
- New tests exercise the actual `_evaluate_and_synthesize` method with mocks:
  1. `test_evaluate_and_synthesize_passes_critique_to_evaluate_sources` — verifies `critique_guidance="Improve source diversity"` reaches `evaluate_sources`
  2. `test_evaluate_and_synthesize_passes_none_without_critique` — verifies `critique_guidance=None` when no critique context
  3. `test_synthesize_final_receives_critique_guidance` — exercises the full standard-mode full_report path (evaluate → draft → skeptic → final) and verifies `critique_guidance="Focus on coverage"` reaches `synthesize_final`
- Added `test_critique_field_populated` to `test_results.py` for the new field
- Added `test_includes_critique_in_result` to `test_public_api.py` for the public API path

## Three Questions

1. **Hardest fix in this batch?** The `ResearchResult.critique` field needed `TYPE_CHECKING` to avoid a circular import (`results.py` → `critique.py`). The `from __future__ import annotations` + `if TYPE_CHECKING` pattern is the standard Python solution, but it's easy to miss and would cause a runtime `ImportError` without it.

2. **What did I consider fixing differently, and why didn't I?** Considered changing `agent.research()` itself to return `ResearchResult` instead of `str`, which would fully satisfy the review's intent. But that would break the CLI and `run_research_async` wrapper — both treat the return as a string. The existing `last_critique` property covers the CLI path, and adding `critique` to `ResearchResult` covers the public API path. Both consumers are now served.

3. **Least confident about going into the next batch or compound phase?** The `test_synthesize_final_receives_critique_guidance` test exercises a long code path (evaluate → draft → skeptic → final) with many mocks. If the internal structure of `_evaluate_and_synthesize` changes (e.g., method extraction), the test will break. This is acceptable for an integration test — it intentionally couples to the real method to catch threading regressions.
