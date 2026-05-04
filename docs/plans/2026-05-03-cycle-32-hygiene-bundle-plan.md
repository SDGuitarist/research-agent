---
feed_forward:
  risk: "api_helpers.py dual-import situation"
  verify_first: true
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

### Commit 1: META_DIR to config.py

Create `research_agent/config.py` with `META_DIR = Path("reports/meta")`.
Update 3 files to import from `config.py` instead of `agent.py`.

| File | Change |
|------|--------|
| `config.py` | **New.** `from pathlib import Path` + `META_DIR = Path("reports/meta")` |
| `agent.py:47` | Remove `META_DIR` definition, add `from .config import META_DIR` |
| `mcp_server.py:191, 340` | Change `from research_agent.agent import META_DIR` to `from research_agent.config import META_DIR`. Remove "accepted private import" comment at line 340. |
| `cli.py:15` | Change `from research_agent.agent import META_DIR` to `from research_agent.config import META_DIR` |

### Commit 2: to_mode_info() on ResearchMode

Add a method to `ResearchMode` that constructs a `ModeInfo`. Simplify
`list_modes()` in `__init__.py`.

| File | Change |
|------|--------|
| `modes.py` | Add `from .results import ModeInfo` at top. Add `to_mode_info()` method that returns `ModeInfo(name=self.name, max_sources=self.max_sources, ...)` with all shared fields. |
| `__init__.py:166-183` | Replace 18-line manual `ModeInfo(...)` construction with `m.to_mode_info()` |
| `tests/test_modes.py` or `tests/test_results.py` | Add test: `to_mode_info()` returns a `ModeInfo` with all fields matching the source `ResearchMode`. Use field-by-field assertion so a new field addition that forgets `to_mode_info` fails immediately. |

### Commit 3: ANTHROPIC_ERRORS consolidation

Replace grouped `except (APIError, RateLimitError, ...)` with
`except ANTHROPIC_ERRORS` at 8 call sites. Leave 3 files untouched.

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

- WHEN `from research_agent.config import META_DIR` is executed THE SYSTEM
  SHALL return `Path("reports/meta")`
- WHEN `ResearchMode.standard().to_mode_info()` is called THE SYSTEM SHALL
  return a `ModeInfo` with `name="standard"`, `max_sources=10`,
  `novelty_queries=1`, and all other fields matching the source mode
- WHEN `list_modes()` is called THE SYSTEM SHALL return the same values as
  before the refactor (verified by snapshot comparison in test)
- WHEN `except ANTHROPIC_ERRORS` is used THE SYSTEM SHALL catch `APIError`,
  `RateLimitError`, `APIConnectionError`, and `APITimeoutError`

### Error Cases

- WHEN a new field is added to `ModeInfo` but not to `to_mode_info()` THE
  SYSTEM SHALL fail the field-completeness test
- WHEN `modes.py` imports from `results.py` THE SYSTEM SHALL not create a
  circular import (verified by `python -c "from research_agent.modes import ResearchMode"`)

### Verification Commands

```bash
# All tests pass
python3 -m pytest tests/ -v

# MCP lint passes
python3 scripts/lint_mcp_parity.py

# No circular import
python3 -c "from research_agent.modes import ResearchMode; print('OK')"

# No remaining inline tuples in converted files (should return 0 matches)
grep -n "except (APIError\|except (RateLimitError" research_agent/context.py research_agent/decompose.py research_agent/iterate.py research_agent/critique.py research_agent/coverage.py research_agent/summarize.py research_agent/search.py

# META_DIR not imported from agent.py anymore (should return 0)
grep -rn "from research_agent.agent import META_DIR" research_agent/

# ANTHROPIC_ERRORS imported in converted files
grep -rn "from research_agent.errors import ANTHROPIC_ERRORS" research_agent/ | wc -l
# Expected: 9 (8 converted files + errors.py definition... actually errors.py defines it, doesn't import it. So 8 files.)
```

## Implementation Order

1. `config.py` + META_DIR (4 files, ~10 lines changed) -- commit
2. `to_mode_info()` (3 files, ~30 lines changed) -- commit
3. ANTHROPIC_ERRORS (10 files, ~40 lines changed) -- commit

Each commit is a checkpoint. If any step breaks tests, fix before proceeding.

## Feed-Forward

- **Hardest decision:** What to do with `agent.py:1127`'s mixed
  `(ResearchError, APIError, ...)` catch. Python doesn't allow tuple unpacking
  in `except` clauses, so `ANTHROPIC_ERRORS` can't be used. Leaving it with a
  comment is the right call -- forcing a workaround would add complexity for
  one site.
- **Rejected alternatives:** Wrapping `(*ANTHROPIC_ERRORS, ResearchError)` in
  a module-level constant (e.g., `RESEARCH_AND_API_ERRORS`) -- too specific,
  only used once, YAGNI.
- **Least confident:** Whether `relevance.py` needs both the `anthropic`
  imports (for lines 280-283) AND `ANTHROPIC_ERRORS` (for line 573). It does,
  but the dual-import in that file looks noisy. Reviewer should confirm this
  is the cleanest approach.

## Three Questions

1. **Hardest decision in this session?** The `agent.py:1127` mixed-tuple site.
   Spent time confirming Python syntax doesn't support `except (*tuple, Type)`.
   Leaving it as-is with a comment is correct.
2. **What did you reject, and why?** A module-level `RESEARCH_AND_API_ERRORS`
   constant for the one mixed-catch site. It's used once, defined far from its
   use, and adds indirection for no real benefit.
3. **Least confident about going into the next phase?** The `relevance.py`
   dual-import. It's correct but visually messy -- two import lines for
   anthropic error types serving different catch blocks. Reviewer should weigh
   in on whether a comment makes it clear enough.
