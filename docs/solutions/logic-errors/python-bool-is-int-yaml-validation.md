---
title: "Python bool-is-int Gotcha in YAML Validation"
date: 2026-02-25
category: logic-errors
tags: [python, isinstance, bool, int, yaml, validation, type-checking]
module: schema.py, context.py
symptoms: "YAML `true`/`false` values silently pass `isinstance(x, int)` checks; priority: true becomes priority 1; dimension scores accept booleans as valid integers"
severity: medium
summary: "In Python, bool is a subclass of int — isinstance(True, int) returns True. YAML parsers map true/false to Python booleans, which then pass integer validation. The fix is to check isinstance(x, bool) before isinstance(x, int)."
---

# Python bool-is-int Gotcha in YAML Validation

## Problem

Gap YAML files and critique YAML files accept integer fields (`priority`, dimension
scores). A user or LLM could write `priority: true` in YAML. Python's YAML parser
converts `true` → `True` (Python bool). The validation `isinstance(priority, int)`
passes because **`bool` is a subclass of `int` in Python**.

```python
>>> isinstance(True, int)
True
>>> isinstance(False, int)
True
>>> True == 1
True
>>> False == 0
True
```

This means:
- `priority: true` → accepted as priority `1`
- `priority: false` → accepted as priority `0` (fails range check if range is 1-5, but passes type check)
- Dimension score `true` → accepted as score `1`

### Where It Happened

Two YAML validation sites accepted booleans as integers:

1. **`schema.py:94`** — Gap priority validation in `_parse_gap()`
2. **`context.py:153`** — Critique dimension score validation in `_validate_critique_yaml()`

## Root Cause

Python's type hierarchy: `bool` inherits from `int`. This is a deliberate language
design choice (PEP 285), not a bug. But it means any `isinstance(x, int)` check
also matches booleans — a common source of validation bugs when processing YAML or
JSON data where `true`/`false` are distinct types from integers.

## Solution

Check for `bool` before checking for `int`:

```python
# WRONG — True/False pass this check
if not isinstance(priority, int):
    raise SchemaError(...)

# CORRECT — reject booleans explicitly, then check int
if isinstance(priority, bool) or not isinstance(priority, int):
    raise SchemaError(f"Gap '{gap_id}' has non-integer priority: {priority!r}")
```

### What Was Changed

1. **`schema.py:94`** — Added `isinstance(priority, bool)` guard before int check
2. **`context.py:153`** — Added `isinstance(val, bool)` guard before int check
3. **`tests/test_context.py`** — Added `test_bool_true_rejected_as_score` test

### Commits

- `8ecfdb3` — Bool guard in context.py with test
- `58425a1` — Bool guard in schema.py (caught by review)

## Prevention

### Rules for Future Development

1. **Every `isinstance(x, int)` check on untrusted data must be preceded by
   `isinstance(x, bool)`** — or use the combined pattern:
   `isinstance(x, bool) or not isinstance(x, int)`.

2. **YAML and JSON parsing always needs this guard.** Both formats distinguish
   booleans from integers at the syntax level, but Python's type system collapses
   that distinction.

3. **Where to apply:** Any validation of data from YAML files, JSON APIs, or
   LLM-generated structured output. Not needed for function parameters that are
   typed by the caller (e.g., frozen dataclass fields set by code).

### Quick Audit Checklist

When adding new `isinstance(x, int)` checks, ask:
- Can `x` come from YAML, JSON, or user input? → Add bool guard
- Is `x` always set by Python code you control? → Bool guard not needed

### Current Codebase Status

All YAML-facing int validations have the bool guard:
- `schema.py:94` — gap priority
- `context.py:153` — critique dimension scores

Typed dataclass fields (`modes.py`, `cycle_config.py`) validate ranges only — safe
because they accept typed parameters from Python code, not raw YAML dicts.

## Cross-References

- [Non-Idempotent Sanitization](../security/non-idempotent-sanitization-double-encode.md) —
  fixed in the same review batch; different bug class, same theme of hidden type behavior
- `docs/reviews/p3-do-now-fixes/REVIEW-SUMMARY.md` — data-integrity-guardian agent
  caught the schema.py instance after context.py was already fixed
- `docs/plans/2026-02-23-p3-do-now-fixes-plan.md` — original fix plan

## Three Questions

1. **Hardest pattern to extract from the fixes?** Deciding how to scope the rule.
   "Always check for bool before int" is too broad — it's unnecessary for typed
   function parameters. The key insight is that this only matters at **data
   deserialization boundaries** (YAML, JSON, external input), not everywhere.

2. **What did you consider documenting but left out, and why?** A `SafeInt` wrapper
   type (similar to the `SanitizedStr` idea in the sanitization doc). Left it out
   because there are only two validation sites, and a wrapper would be over-engineering
   at this scale. The `isinstance(x, bool)` guard is simple and self-documenting.

3. **What might future sessions miss that this solution doesn't cover?** Python's
   `float` has no bool subclass problem, but YAML does have other type coercion
   surprises — `yes`/`no`/`on`/`off` all map to booleans in YAML 1.1 (PyYAML's
   default). If a future field expects a string like `"yes"`, YAML will silently
   convert it to `True`. The fix there is different (quoting in YAML), but the
   root cause — YAML's implicit type coercion — is the same family of bugs.
