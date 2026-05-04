---
title: "Constant Consolidation and Dataclass Conversion Methods"
category: architecture
tags: [refactoring, imports, frozen-dataclass, exception-handling, constants]
module: modes.py, report_store.py, errors.py
cycle: 32
symptom: "Same 4-exception tuple copy-pasted across 10+ files; META_DIR imported from heavy orchestrator; 18-line manual field mapping repeated every time ModeInfo fields change"
root_cause: "Organic growth over 31 cycles without periodic consolidation"
---

# Constant Consolidation and Dataclass Conversion Methods

**Date:** 2026-05-03
**Cycle:** 32 (hygiene bundle)
**Trigger:** 3 deferred items from Cycle 29H audit and Cycle 31 review
**Sessions:** 1 work + 1 review (4 agents)

## Problem

After 31 development cycles, three maintenance taxes accumulated:

1. **ANTHROPIC_ERRORS** tuple `(APIError, RateLimitError, APIConnectionError, APITimeoutError)` was copy-pasted in 10+ files. Adding a 5th exception type would require hunting across the codebase.
2. **META_DIR** was defined in `agent.py` (the heavy orchestrator), forcing lightweight modules (`mcp_server.py`, `cli.py`) to import the entire orchestrator just for a path constant.
3. **ModeInfo construction** required 18 lines of manual field mapping in `list_modes()`. Every new field on `ResearchMode` needed updates in 6 locations (the "6-file sync tax" flagged in Cycles 19, 26, 27, 28, 30, 31).

## Solution

### 1. Path constants live with their owning module

Moved `META_DIR = Path("reports/meta")` from `agent.py` to `report_store.py`, next to `REPORTS_DIR = Path("reports")`.

**Pattern discovered during 7-agent plan deepening:** This codebase already follows "constant lives with its owning module" (`REPORTS_DIR` in `report_store.py`, `CONTEXTS_DIR` in `context.py`). Three agents recommended three different locations:

| Agent | Location | Reasoning |
|-------|----------|-----------|
| Simplicity | `errors.py` | Already holds shared constants |
| Architecture | `config.py` | Standard pattern (Django settings.py) |
| Patterns | `report_store.py` | Follows existing codebase convention |

**Decision:** `report_store.py`. A hygiene cycle should strengthen existing patterns, not introduce new ones. `report_store.py` is also lightweight (re, datetime, pathlib), so `mcp_server.py`'s lazy imports avoid loading the heavy orchestrator.

**Key insight:** `cli.py` gets zero import-time benefit because it already eagerly imports `agent.py` through `__init__.py`. Only `mcp_server.py` benefits (confirmed by performance reviewer).

### 2. Explicit field mapping on the source dataclass

Added `to_mode_info()` to `ResearchMode` with explicit field-by-field construction of `ModeInfo`. Two approaches were debated:

| Approach | Pros | Cons |
|----------|------|------|
| Explicit mapping (chosen) | TypeError on missing required field, readable | Must update when fields change |
| Dict-based (`dataclasses.asdict` + filter) | Auto-tracks new fields | Silently swallows missing fields, deep-copies unnecessarily |

**Decision:** Explicit mapping. For a codebase that struggled with 6-file sync drift across 6 cycles, loud failure (TypeError) is more valuable than convenience.

**Guard against circular imports:** `modes.py` now imports from `results.py`. Added `# NOTE: modes.py imports from this module. Do not import from modes here.` to `results.py`. This is a comment guardrail, not enforcement -- if a second cross-leaf import appears, escalate to a `converters.py` module.

**Test strategy:** Uses `dataclasses.fields(ModeInfo)` to programmatically verify every ModeInfo field appears in the output. Self-updating when fields are added to either class.

### 3. Adopt shared exception constant, not consolidate

`ANTHROPIC_ERRORS` was already defined in `errors.py` (from Cycle 29H) but never consumed. Adopted it at 10 call sites across 9 files. Key edge cases:

| Situation | Decision | Why |
|-----------|----------|-----|
| Per-type catches (`skeptic.py`, `synthesize.py`) | Leave untouched | Per-type log messages are intentional |
| Mixed tuple (`agent.py:1126`) | Leave with comment | Python doesn't allow `except (ResearchError, *ANTHROPIC_ERRORS)` |
| Dual-import (`relevance.py`, `api_helpers.py`) | Keep both import sources | Individual types needed for per-type catches or default parameters |

## Key Patterns

### 1. When 3+ agents disagree, pick the one that matches existing conventions

The META_DIR debate had three credible answers. The pattern-matching argument won because a hygiene cycle should reinforce patterns, not invent new ones. Save architectural innovation for feature cycles.

### 2. Loud failure > automatic convenience for drift-prone mappings

The dict-based ModeInfo constructor was elegant but silent. When a mapping has drifted 6 times across 6 cycles, you want TypeError, not a default value.

### 3. Python `except` clauses don't support tuple unpacking

`except (ResearchError, *ANTHROPIC_ERRORS)` is invalid Python syntax. There is no clean workaround -- a module-level combined constant (`RESEARCH_AND_API_ERRORS`) is YAGNI for a single call site. Leave the inline tuple with a comment.

### 4. Verify before removing imports

Before replacing `from anthropic import APIError, ...` with `ANTHROPIC_ERRORS`, verify each exception type isn't used elsewhere in the file (isinstance checks, default parameters, type hints). Two files needed dual imports for legitimate reasons.

### 5. Comment guardrails have a shelf life

The `# Do not import from modes here` comment in `results.py` works for a solo maintainer but won't scale. If this codebase grows contributors, replace with a linting rule or import-graph test.

## Prevention

- Run `ANTHROPIC_ERRORS` adoption in the same cycle that defines it, not deferred. The 2-cycle gap (29H define, 32 adopt) let 2 more cycles of copy-paste accumulate.
- When adding a field to a frozen dataclass that has a conversion method, the TypeError from explicit mapping catches it immediately. No separate "field sync" checklist needed.
- When moving a constant, grep for it in tests too (this time tests had no mocks, but next time they might).

## Three Questions

1. **Hardest pattern to extract from the fixes?** The "3 agents disagree" resolution pattern. It's tempting to pick the most architecturally pure answer, but for hygiene work, convention compliance beats innovation.
2. **What did you consider documenting but left out, and why?** The full 7-agent deepening review debate. It's in the plan doc already -- duplicating it here would be noise. This doc captures the conclusions, the plan doc has the deliberation.
3. **What might future sessions miss that this solution doesn't cover?** The `modes.py -> results.py` import edge. If someone adds `from .modes import ...` to `results.py`, the circular import won't be caught until runtime. A CI rule (import-graph linter) would be more durable than a comment.
