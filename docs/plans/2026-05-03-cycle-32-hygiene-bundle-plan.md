---
feed_forward:
  risk: "modes.py -> results.py import edge between leaf modules"
  verify_first: false
---

# Cycle 32 Plan: Hygiene Bundle

**Date:** 2026-05-03
**Brainstorm:** `docs/brainstorms/2026-05-03-cycle-32-hygiene-bundle-brainstorm.md`
**Branch:** `chore/32-hygiene-bundle`

## Prior Phase Risk

> "The `api_helpers.py` import strategy. It uses `RateLimitError` as a default
> parameter value in `retry_on=(RateLimitError,)`, which means the individual
> import can't be removed even if we add ANTHROPIC_ERRORS."
> -- Cycle 32 brainstorm, "Least confident"

**Verified.** Read `api_helpers.py`. Line 56 has the grouped catch (replaceable
with `ANTHROPIC_ERRORS`). Lines 32 and 60 use `RateLimitError` individually
for the default parameter and isinstance check. Result: replace
`from anthropic import APIConnectionError, APIError, APITimeoutError, RateLimitError`
with `from anthropic import RateLimitError` + `from research_agent.errors import ANTHROPIC_ERRORS`.
Clean dual-import, not awkward.

## What exactly is changing?

Three mechanical refactors, each in its own commit:

### Commit 1: META_DIR to report_store.py

Move `META_DIR` from `agent.py` to `report_store.py`, next to `REPORTS_DIR`.
This follows the existing codebase pattern where path constants live in the
module that owns them (`REPORTS_DIR` is already in `report_store.py`, and
`META_DIR = Path("reports/meta")` is a subdirectory of it). No new file needed.

`report_store.py` is lightweight (only `re`, `datetime`, `pathlib`, `.results`),
so `mcp_server.py`'s lazy imports still avoid loading the heavy `agent.py`
orchestrator. Note: `cli.py` gets no import-time benefit because it already
eagerly imports `agent.py` through `from research_agent import ResearchAgent`.

Also audit docstrings and comments for stale references to META_DIR's old
location in `agent.py`.

| File | Change |
|------|--------|
| `report_store.py:9` | Add `META_DIR = Path("reports/meta")` below `REPORTS_DIR` |
| `agent.py:47` | Remove `META_DIR` definition, add `from .report_store import META_DIR` |
| `mcp_server.py:191, 340` | Change `from research_agent.agent import META_DIR` to `from research_agent.report_store import META_DIR`. Remove "accepted private import" comment at line 340. |
| `cli.py:15` | Change `from research_agent.agent import META_DIR` to `from research_agent.report_store import META_DIR` |

**Why not config.py?** Pattern recognition review found that this codebase
keeps path constants in the module that owns them (REPORTS_DIR in
report_store.py, CONTEXTS_DIR in context.py). Creating a new file for a single
constant breaks this pattern.

**Why not errors.py?** Although it holds ANTHROPIC_TIMEOUT, a filesystem path
constant is semantically unrelated to errors and exceptions.

### Commit 2: to_mode_info() on ResearchMode

Add a method to `ResearchMode` that constructs a `ModeInfo`. Simplify
`list_modes()` in `__init__.py`.

| File | Change |
|------|--------|
| `modes.py` | Add `from .results import ModeInfo` at top. Add `to_mode_info()` method using **explicit field mapping** (Approach A) -- returns `ModeInfo(name=self.name, max_sources=self.max_sources, ...)` with all shared fields. Explicit mapping ensures a missing required field triggers `TypeError` at construction time, not silent drift. |
| `results.py` | Add comment at top of file: `# NOTE: modes.py imports from this module. Do not import from modes here.` |
| `__init__.py:166-183` | Replace 18-line manual `ModeInfo(...)` construction with `m.to_mode_info()` |
| `tests/test_modes.py` | Add test: `to_mode_info()` returns a `ModeInfo` with all fields matching the source `ResearchMode`. Use `dataclasses.fields(ModeInfo)` to programmatically verify every ModeInfo field appears in the output -- this makes the test self-updating when fields are added to either class. |

### Commit 3: ANTHROPIC_ERRORS consolidation

Adopt the existing `ANTHROPIC_ERRORS` constant (already defined at
`errors.py:11`) at 8 call sites that currently inline the tuple. Leave 3
files untouched.

**Replace (8 sites in 8 files):**

| File | Line | Notes |
|------|------|-------|
| `api_helpers.py:56` | Replace grouped catch. Keep `from anthropic import RateLimitError` (used at lines 32, 60). Remove other 3 individual imports. |
| `context.py:443` | Replace grouped catch. Remove all 4 `anthropic` imports. |
| `decompose.py:176` | Replace grouped catch. Remove all 4 `anthropic` imports. |
| `iterate.py:99, 223` | Replace both grouped catches. Remove all 4 `anthropic` imports. |
| `critique.py:221` | Replace grouped catch. Remove all 4 `anthropic` imports. |
| `coverage.py:267` | Replace grouped catch. Remove all 4 `anthropic` imports. |
| `summarize.py:186` | Replace grouped catch. Remove all 4 `anthropic` imports. |
| `search.py:295` | Replace grouped catch. Remove all 4 `anthropic` imports. |
| `relevance.py:573` | Replace grouped catch. Keep `from anthropic import ...` for line 280 per-type catches (see below). |

**Leave untouched (3 files):**

| File | Reason |
|------|--------|
| `skeptic.py` | 4 individual `except` blocks with per-type log messages |
| `synthesize.py` | Same pattern -- per-type logging is intentional |
| `relevance.py:280-283` | `RateLimitError` caught separately from `(APIError, APIConnectionError, APITimeoutError)` with different messages. This is a 3-type subset, not the full tuple. Leave as-is. |

**Special case:**

| File | Situation |
|------|-----------|
| `agent.py:1127` | Catches `(ResearchError, APIError, RateLimitError, APIConnectionError, APITimeoutError)`. Can't use `ANTHROPIC_ERRORS` without tuple unpacking: `except (ResearchError, *ANTHROPIC_ERRORS)` is invalid Python syntax in except clauses. Leave as-is, or use `except (*ANTHROPIC_ERRORS, ResearchError)` -- **wait, that's also invalid.** Leave this site as-is and add a comment: `# ResearchError + ANTHROPIC_ERRORS (can't unpack in except clause)`. |

**Import pattern per file after consolidation:**

```python
# Files with only grouped catches:
from research_agent.errors import ANTHROPIC_ERRORS

# api_helpers.py (needs RateLimitError individually):
from anthropic import RateLimitError
from research_agent.errors import ANTHROPIC_ERRORS

# relevance.py (needs individual types for line 280-283):
# Individual imports for per-type catches (line ~280); ANTHROPIC_ERRORS for grouped catch (line ~573)
from anthropic import AsyncAnthropic, APIConnectionError, APIError, APITimeoutError, RateLimitError
from research_agent.errors import ANTHROPIC_ERRORS
```

## What must not change?

- **Exception handling behavior.** Every `except` clause must catch the same
  types as before. No new exceptions caught, no exceptions dropped.
- **META_DIR value.** Still `Path("reports/meta")`. Just a different import path.
- **ModeInfo fields.** `to_mode_info()` must produce identical output to the
  current manual construction in `list_modes()`.
- **Public API.** `list_modes()` return type and values unchanged.
- **Test count.** All existing tests pass. Only new tests are for `to_mode_info()`.

## Acceptance Tests

### Happy Path

- WHEN `from research_agent.report_store import META_DIR` is executed THE
  SYSTEM SHALL return `Path("reports/meta")`
- WHEN `ResearchMode.standard().to_mode_info()` is called THE SYSTEM SHALL
  return a `ModeInfo` with `name="standard"`, `max_sources=10`,
  `novelty_queries=1`, and all other fields matching the source mode
- WHEN `list_modes()` is called THE SYSTEM SHALL return the same values as
  before the refactor (verified by snapshot comparison in test)
- WHEN `except ANTHROPIC_ERRORS` is used THE SYSTEM SHALL catch `APIError`,
  `RateLimitError`, `APIConnectionError`, and `APITimeoutError`

### Error Cases

- WHEN a new field is added to `ModeInfo` but not to `to_mode_info()` THE
  SYSTEM SHALL fail the `dataclasses.fields()`-based completeness test
- WHEN `modes.py` imports from `results.py` THE SYSTEM SHALL not create a
  circular import (verified by importing from both entry points)
- WHEN a new field is added to `ModeInfo` but not to `to_mode_info()` THE
  SYSTEM SHALL raise `TypeError` at construction time (explicit mapping)

### Verification Commands

```bash
# All tests pass
python3 -m pytest tests/ -v

# MCP lint passes
python3 scripts/lint_mcp_parity.py

# No circular import (check both directions)
python3 -c "from research_agent.modes import ResearchMode; print('modes OK')"
python3 -c "from research_agent.results import ModeInfo; print('results OK')"

# No remaining inline tuples in converted files (should return 0 matches)
grep -n "except (APIError\|except (RateLimitError" research_agent/context.py research_agent/decompose.py research_agent/iterate.py research_agent/critique.py research_agent/coverage.py research_agent/summarize.py research_agent/search.py

# META_DIR not imported from agent.py anymore (should return 0)
grep -rn "from research_agent.agent import META_DIR" research_agent/

# META_DIR now imported from report_store.py
grep -rn "from.*report_store import META_DIR" research_agent/

# ANTHROPIC_ERRORS adopted in converted files (expected: 8 files)
grep -rn "from research_agent.errors import ANTHROPIC_ERRORS" research_agent/ | wc -l
```

## Implementation Order

1. META_DIR to `report_store.py` (4 files, ~10 lines changed) -- commit
2. `to_mode_info()` (4 files, ~30 lines changed) -- commit
3. ANTHROPIC_ERRORS adoption (10 files, ~40 lines changed) -- commit

Each commit is a checkpoint. If any step breaks tests, fix before proceeding.

## Deepening Review (2026-05-03)

Plan deepened with 7 parallel review agents: plan quality gate, Python
reviewer, architecture strategist, pattern recognition, code simplicity,
performance oracle, learnings researcher, and security sentinel.

### Key Changes From Review

1. **META_DIR location changed from `config.py` to `report_store.py`.**
   Pattern recognition found that this codebase keeps path constants in the
   module that owns them (REPORTS_DIR in report_store.py, CONTEXTS_DIR in
   context.py). Creating a new file for one constant broke the pattern.
   Architecture reviewer favored config.py, simplicity reviewer favored
   errors.py. Chose report_store.py as the best semantic fit -- META_DIR is
   a subdirectory of REPORTS_DIR. report_store.py is lightweight (re, datetime,
   pathlib, .results), so mcp_server.py lazy-import benefit is preserved.
   Performance reviewer confirmed cli.py gets no import-time benefit either way.

2. **to_mode_info() uses explicit field mapping (Approach A), not dict-based.**
   Python reviewer argued TypeError on missing required field is better than
   silent drift. Simplicity reviewer preferred dict-based (auto-tracks fields).
   Chose explicit: it fails loudly and is more readable for this codebase.
   Added `# Do not import from modes here` guard in results.py per Python
   reviewer. Test uses `dataclasses.fields()` comparison per patterns reviewer.

3. **Clarified that ANTHROPIC_ERRORS already exists** -- Commit 3 adopts it
   at 8 call sites, not creates it. Added clarifying comment for relevance.py
   dual-import. Security reviewer verified all 8 sites are type-equivalent.

### Agents That Found No Issues
- Security sentinel: zero new attack surface, all exception catches equivalent
- Performance oracle: all 3 refactors performance-neutral at runtime

## Feed-Forward

- **Hardest decision:** Where to put META_DIR. Three agents recommended three
  different locations. Chose `report_store.py` because it follows the existing
  codebase pattern (constant lives with its owning module) and META_DIR is
  semantically a subdirectory of REPORTS_DIR.
- **Rejected alternatives:** `config.py` (breaks existing pattern, YAGNI for
  one constant), `errors.py` (semantically unrelated to errors),
  `ModeInfo.from_mode()` classmethod (less natural read direction),
  dict-based `to_mode_info()` (silently swallows new fields instead of
  raising TypeError), `RESEARCH_AND_API_ERRORS` constant (YAGNI, used once).
- **Least confident:** Whether the `modes.py -> results.py` import edge will
  cause problems in future cycles. The `# Do not import from modes here`
  comment in results.py is a guardrail but not enforcement. If a second
  cross-leaf import appears, reconsider the boundary.

## Three Questions

1. **Hardest decision in this session?** META_DIR location. Three credible
   options from three different reviewers. The pattern-matching argument
   (constant lives with its owning module) won because a hygiene cycle should
   strengthen existing patterns, not introduce new ones.
2. **What did you reject, and why?** Dict-based ModeInfo constructor
   (`dataclasses.asdict` + field filtering). It's clever and auto-tracks
   fields, but silently swallows new required fields instead of failing with
   TypeError. For a codebase that has struggled with 6-file sync drift across
   6 cycles, loud failure is more valuable than convenience.
3. **Least confident about going into the next phase?** The `modes.py ->
   results.py` import creates a new dependency edge between two previously
   independent leaf modules. It's safe today, but narrows future flexibility.
   If this becomes a recurring pattern, a `converters.py` module may be needed.
