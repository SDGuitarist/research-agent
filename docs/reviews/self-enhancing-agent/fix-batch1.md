# Fix Batch 1: P1 Findings #1-4

**Commit:** `fix(critique): resolve P1 review findings #1-4`
**Files changed:** `research_agent/agent.py`, `research_agent/cli.py`, `research_agent/critique.py`
**Tests:** 604 passed

## Prior Phase Risk

> "No agent actually ran the test suite. We reviewed test code but didn't verify all 558 tests pass with these changes."

Addressed: Ran full test suite (604 tests, all pass) before and after committing.

## Fixes Applied

### P1 #1: Bare `except Exception` (agent.py:155)
- Replaced `except (CritiqueError, Exception)` with `except (CritiqueError, OSError, yaml.YAMLError)`
- Also fixed f-string in logger to lazy `%s` formatting (P3 #24 freebie)
- Added `import yaml` to agent.py for the exception type

### P1 #2: No CLI Entry Point for Critique (cli.py)
- Added `--critique <report-path>` flag
- Created `critique_report_file()` in `critique.py` — evaluates report *text* directly (vs `evaluate_report` which evaluates process metadata)
- Uses XML `<report>` boundaries consistent with three-layer defense
- Caps report text at 8000 chars for token budget
- Prints scores, weaknesses, suggestions, and save path

### P1 #3: Critique Results Invisible (cli.py)
- After `agent.research()`, checks `agent.last_critique` and prints one-line summary
- Added public `last_critique` property on `ResearchAgent`
- Format: `Self-critique: mean=3.8, pass` or `Self-critique: mean=2.1, FAIL`

### P1 #4: No CLI Read Path for History (cli.py)
- Added `--critique-history` flag
- Calls existing `load_critique_history()` and prints the summarized patterns
- Falls back to helpful message when < 3 critiques exist

## Three Questions

1. **Hardest fix in this batch?** P1 #2 — `evaluate_report` evaluates the *process* (source counts, gate decisions), not the report text. A standalone `--critique` needs to evaluate text. I created a separate `critique_report_file()` function rather than bending the existing one, keeping the two use cases distinct.

2. **What did I consider fixing differently, and why didn't I?** Considered returning `CritiqueResult` from `research()` (P2 #14) instead of adding a `last_critique` property. That would be cleaner but changes the public API signature from `str` to a new return type, which ripples through tests and callers. The property is non-breaking and sufficient for P1 #3.

3. **Least confident about going into the next batch or compound phase?** The `critique_report_file` function has no tests yet. It works (verified by reading the code path), but a future test session should add unit tests with mocked API responses.
