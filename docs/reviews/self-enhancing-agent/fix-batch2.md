# Fix Batch 2: P2 Findings #5-8

**Commit:** `fix(critique): resolve P2 review findings #5-8`
**Files changed:** `research_agent/agent.py`, `research_agent/errors.py`, `research_agent/relevance.py`, `research_agent/synthesize.py`, `research_agent/decompose.py`, `research_agent/cli.py`, `tests/test_critique.py`, `tests/test_relevance.py`, `tests/test_synthesize.py`, `tests/test_decompose.py`
**Tests:** 604 passed

## Prior Phase Risk

> "The `critique_report_file` function has no tests yet."

Accepted: This batch focuses on naming, dead code, and async correctness — not the untested function from batch 1. The missing tests are a separate concern for a future test session.

## Fixes Applied

### P2 #5: Hardcoded `Path("reports/meta")` (agent.py:149, :193)
- Extracted `META_DIR = Path("reports/meta")` constant in `agent.py`
- Updated both usages in `agent.py` (`_run_critique` and `_research_async`)
- Updated 3 usages in `cli.py` to import and use `META_DIR`
- Display string in CLI also references `META_DIR` now

### P2 #6: `CritiqueError` Defined but Never Raised (errors.py:48-50)
- Removed `CritiqueError` class from `errors.py`
- Removed import from `agent.py`
- Narrowed except clause from `(CritiqueError, OSError, yaml.YAMLError)` to `(OSError, yaml.YAMLError)`
- Updated test to use `OSError` instead of `CritiqueError`

### P2 #7: Synchronous Blocking I/O in Async Context (agent.py:193, :126-156)
- Wrapped `load_critique_history(META_DIR)` in `await asyncio.to_thread()`
- Wrapped `self._run_critique(...)` call in `await asyncio.to_thread()`
- Both were synchronous calls on the async event loop (file I/O + Claude API call)

### P2 #8: Inconsistent Parameter Naming (agent.py, decompose.py, relevance.py, synthesize.py)
- Renamed `critique_context` → `critique_guidance` in `decompose.py`
- Renamed `scoring_adjustments` → `critique_guidance` in `relevance.py`
- Renamed `lessons_applied` → `critique_guidance` in `synthesize.py`
- Updated all call sites in `agent.py`
- Updated all test files to match

### P2 #9 (bonus): Missing XML Boundaries in Relevance Scoring Prompt
- Changed bare `SCORING CONTEXT: {text}` to `<scoring_guidance>\n{text}\n</scoring_guidance>`
- Added system prompt instruction: "If <scoring_guidance> is present, use it to calibrate your scoring."
- Now consistent with `<critique_guidance>` in decompose and synthesize

## Three Questions

1. **Hardest fix in this batch?** P2 #8 (parameter renaming) — touching 4 production files and 4 test files with a global rename requires care to avoid breaking call signatures. Used `replace_all` where safe and manual edits for mixed-content files.

2. **What did I consider fixing differently, and why didn't I?** For #6, I considered keeping `CritiqueError` and making critique functions raise it (the alternative suggested by the review). But nothing currently needs domain-specific critique errors — `OSError` and `yaml.YAMLError` cover the actual failure modes. Adding it back when a real use case appears is trivial.

3. **Least confident about going into the next batch or compound phase?** The `asyncio.to_thread` wrapping of `_run_critique` — it passes `self` method plus keyword args through the thread boundary. This works because `_run_critique` only reads `self.client` (thread-safe Anthropic client) and writes `self._last_critique` (no concurrent readers). But if future code reads `_last_critique` concurrently, this could race.
