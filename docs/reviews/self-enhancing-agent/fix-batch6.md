# Fix Batch 6: P2 Findings #16-18

**Commit:** `fix(critique): fix filtering docstring, add missing param docs, add --no-critique (#16-18)`
**Files changed:** `research_agent/context.py`, `research_agent/decompose.py`, `research_agent/agent.py`, `research_agent/cli.py`
**Tests:** 608 passed

## Prior Phase Risk

> "The `test_synthesize_final_receives_critique_guidance` test exercises a long code path (evaluate → draft → skeptic → final) with many mocks. If the internal structure of `_evaluate_and_synthesize` changes (e.g., method extraction), the test will break."

Accepted: This batch doesn't modify `_evaluate_and_synthesize`, so the coupling risk doesn't apply.

## Fixes Applied

### P2 #16: `_summarize_patterns` Filtering Logic Confusing
- Moved the `overall_pass` filter from `_summarize_patterns` to `load_critique_history`
- `load_critique_history` now pre-filters to passing critiques before the count check and the call to `_summarize_patterns`
- `_summarize_patterns` renamed parameter to `passing_critiques` and updated docstring to clarify it expects pre-filtered input
- Count check is now honest: "fewer than 3 valid passing critiques" matches reality
- Updated `load_critique_history` docstring to say "passing critiques"

### P2 #17: Missing Docstring for `critique_guidance` Parameter
- Added `model` and `critique_guidance` to the `decompose_query` docstring Args block
- Both were present in the function signature but undocumented

### P2 #18: No `--no-critique` CLI Flag
- Added `skip_critique: bool = False` parameter to `ResearchAgent.__init__`
- `_run_critique` checks `self.skip_critique` alongside the existing quick-mode guard
- Added `--no-critique` CLI flag with help text "Skip post-report self-critique (saves one API call)"
- CLI passes `args.no_critique` to agent constructor
- Critique history loading for adaptive prompts is unaffected — `--no-critique` only skips the post-report evaluation API call

## Three Questions

1. **Hardest fix in this batch?** The `_summarize_patterns` refactor (#16). The double-filtering was subtle — `load_critique_history` checked `len(valid_critiques) >= 3` but `_summarize_patterns` internally filtered to passing only, so 5 valid critiques with only 2 passing would pass the outer check but return empty from the inner one. Pre-filtering in the caller makes both checks agree.

2. **What did I consider fixing differently, and why didn't I?** For #18, considered making `--no-critique` also skip loading critique history (the file reads in `_research_async`). Decided against it because critique history improves prompt quality at near-zero cost (just YAML reads), while the API call in `_run_critique` is the expensive part users want to skip.

3. **Least confident about going into the next batch or compound phase?** The `--no-critique` flag has no dedicated test. The existing `test_quick_mode_skips_critique` test covers the early-return path in `_run_critique`, and the `skip_critique` check uses the same code path. A test that constructs `ResearchAgent(skip_critique=True)` and verifies `_run_critique` returns early would be quick to add but wasn't in scope for this batch.
