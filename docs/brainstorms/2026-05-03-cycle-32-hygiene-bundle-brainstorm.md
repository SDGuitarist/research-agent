# Cycle 32 Brainstorm: Hygiene Bundle

**Date:** 2026-05-03
**Type:** Mechanical cleanup (bundled micro-cycle)
**Prior cycle:** 31 (novelty decomposition + MCP critique history)

## Prior Phase Risk

> "Whether the novelty prompt instruction will produce meaningfully different
> sub-queries without being so vague that it degrades decomposition quality."
> -- Cycle 31 brainstorm, "Least confident"

This cycle does not touch decomposition or novelty logic. The risk remains
open and will be addressed by the deferred A/B validation item when API keys
are renewed. Accepted as-is for this hygiene cycle.

## Goal

Bundle three small deferred items into one cycle to reduce maintenance tax
before the next feature cycle:

1. **ANTHROPIC_ERRORS consolidation** -- replace ~10 grouped inline exception
   tuples with the shared constant from `errors.py`
2. **META_DIR promotion** -- move from `agent.py` private constant to a shared
   location importable without reaching into `agent`
3. **`to_mode_info()` method** -- add to `ResearchMode` so `ModeInfo`
   construction is co-located with the dataclass it mirrors

## Context

### Item 1: ANTHROPIC_ERRORS

**Current state:** `errors.py:11` defines
`ANTHROPIC_ERRORS = (APIError, RateLimitError, APIConnectionError, APITimeoutError)`.
Zero files import it. All 11 modules import the 4 types directly from
`anthropic` and assemble their own tuples in `except` clauses.

**Scope:** 12 files have inline exception tuples. ~10 sites use grouped
`except (APIError, RateLimitError, ...)` and can switch to
`except ANTHROPIC_ERRORS`. Exact per-site audit deferred to plan phase.

**Exceptions (do NOT consolidate):**
- `skeptic.py` -- 4 individual `except` blocks with per-type log messages
- `synthesize.py` -- same pattern, per-type logging is intentional

These two files keep their direct `anthropic` imports. Don't force the
constant where per-type handling exists.

### Item 2: META_DIR

**Current state:** Defined at `agent.py:47` as `META_DIR = Path("reports/meta")`.
Used by 4 sites:
- `agent.py:224, 447` (defines and uses it internally)
- `mcp_server.py:191, 340` (via `from research_agent.agent import META_DIR`)
- `cli.py:15` (via `from research_agent.agent import META_DIR`)

**Problem:** Importing from `agent.py` pulls in a heavy module (the
orchestrator) just for a path constant. `mcp_server.py` even has a comment
acknowledging it: "accepted private import (see plan S4)".

**Decision:** New `config.py` -- the natural home for shared path constants.
Tiny file (under 10 lines). Follows the Cycle 29H pattern of moving hardcoded
values to a config surface (`EXTRACT_DOMAINS` to context profile). Rejected
alternatives captured in Feed-Forward.

### Item 3: to_mode_info()

**Current state:** `__init__.py:157-185` manually maps every `ResearchMode`
field to a `ModeInfo` constructor call in `list_modes()`. When a field is
added to `ResearchMode` (like `novelty_queries` in Cycle 31), you must also
add it to `ModeInfo` and update the manual mapping -- 6 files touched for
one field.

**Design decision:** Where does the method live?

- On `ResearchMode` (in `modes.py`) -- but `ModeInfo` is defined in
  `results.py`, so `modes.py` would need to import from `results.py`.
  Currently `modes.py` has zero local imports. Adding one is fine --
  `results.py` doesn't import from `modes.py`, so no circular dependency.
- On `ModeInfo` as a classmethod `from_mode(mode: ResearchMode)` -- but
  `results.py` would need to import `ResearchMode` from `modes.py`. Also
  fine, no circular dep.

**Decision:** Method on `ResearchMode` (`to_mode_info()`) because the
conversion direction is "I have a mode, give me its info." This reads
naturally: `mode.to_mode_info()`. The import of `ModeInfo` into `modes.py`
is lightweight.

**What changes:**
- `modes.py`: Add `from .results import ModeInfo` and `to_mode_info()` method
- `__init__.py`: Replace 18-line manual mapping with
  `[m.to_mode_info() for m in modes]`
- `mcp_server.py`: Use `mode.to_mode_info()` if it constructs ModeInfo
  anywhere (check during planning)
- Tests: Add test that `to_mode_info()` round-trips all fields

## Scope

### In scope
- ANTHROPIC_ERRORS import replacement (~10 call sites)
- New `config.py` with `META_DIR`; update 4 import sites (agent, mcp_server x2, cli)
- `to_mode_info()` method on `ResearchMode`; simplify `list_modes()`
- Tests for `to_mode_info()` field completeness
- MCP lint passes (8/8 tools)

### Out of scope
- Changing exception handling behavior (just import paths)
- Changing META_DIR value or adding new config constants
- Moving other constants into `config.py` (scope creep risk -- just META_DIR)
- Changing ModeInfo fields (just relocating construction)
- Anything touching novelty, decomposition, or synthesis logic
- A/B testing or threshold tuning

## Risks

- **Circular imports:** `modes.py` importing from `results.py`. Low risk --
  verified no reverse dependency exists.
- **Missed call site:** Grep found all sites, but a dynamic import could hide
  one. Tests will catch it (any bare `from anthropic import APIError` in a
  file that only uses the grouped pattern is a miss).
- **`api_helpers.py` special case:** This file uses individual exception types
  for retry logic (`retry_on=(RateLimitError,)` default parameter). It needs
  to keep individual imports alongside `ANTHROPIC_ERRORS` for its grouped
  catch. Plan must note this.

## Implementation Approach

Dependency order:
1. **config.py + META_DIR** first (no dependencies on the other two)
2. **to_mode_info()** second (no dependencies on ANTHROPIC_ERRORS)
3. **ANTHROPIC_ERRORS** third (widest file spread, benefits from the other
   two being committed as checkpoints)

Each item gets its own commit (~30-50 lines each).

## Feed-Forward

- **Hardest decision:** Where to put META_DIR. `config.py` adds a file but is
  semantically correct. Putting it in an existing file would be expedient but
  wrong.
- **Rejected alternatives:** META_DIR in `modes.py` (wrong domain), META_DIR
  in `errors.py` (wrong domain), `ModeInfo.from_mode()` classmethod (less
  natural read direction than `mode.to_mode_info()`).
- **Least confident:** Whether `api_helpers.py` needs special handling -- it
  uses both individual exceptions (for retry logic defaults) and a grouped
  catch. Need to read it carefully during planning to confirm the right
  import strategy.

## Three Questions

1. **Hardest decision in this session?** Where to place META_DIR. Every
   existing file was semantically wrong. A new `config.py` is the right call
   even though it adds a file to the project.
2. **What did you reject, and why?** Consolidating skeptic.py and
   synthesize.py per-type catches into ANTHROPIC_ERRORS. The per-type logging
   is intentional and valuable for debugging -- forcing a grouped catch would
   lose that signal.
3. **Least confident about going into the next phase?** The `api_helpers.py`
   import strategy. It uses `RateLimitError` as a default parameter value in
   `retry_on=(RateLimitError,)`, which means the individual import can't be
   removed even if we add ANTHROPIC_ERRORS. Need to verify this doesn't
   create an awkward dual-import situation.
