---
title: "Extract public parse_context_file wrapper to eliminate private import coupling"
date: 2026-03-08
cycle: 25
category: architecture
problem_type: api-hygiene
component: context.py
severity: low
resolution_time: 1 session
tags: [refactor, public-api, coupling, housekeeping, deferred-debt]
related_cycles: [24]
---

# Public Wrapper for Cross-Module Access

## Problem

`research_agent/cli.py` imported `_parse_template`, a private function from `context.py`, to support the `--list-contexts` CLI flag. This created fragile coupling to an internal implementation detail — any rename or signature change to `_parse_template` would break the CLI module. The issue was flagged as coupling debt during cycle 24 with a note to extract a public wrapper when needed.

## Root Cause

When `--list-contexts` was added in cycle 24, importing the existing private parser was the quickest path. No public API existed for parsing a single context file outside of the full `load_full_context()` flow.

## Solution

1. **Added `parse_context_file()` public wrapper in `context.py`** — a thin delegate with identical signature:
   ```python
   def parse_context_file(
       raw: str,
   ) -> tuple[str, ReportTemplate | None, ContextProfile | None]:
       return _parse_template(raw)
   ```

2. **Updated `cli.py` import** — replaced the private import:
   ```python
   # Before
   from research_agent.context import _parse_template
   # After
   from research_agent.context import parse_context_file
   ```

3. **Switched all 22 test call sites** in `test_context.py` to use `parse_context_file`. Audit confirmed all 22 tested the public contract (string in → tuple out), none tested internal implementation details.

4. **Added `parse_context_file` to `__init__.py` exports** — consistent with other context functions already exported.

5. **Internal callers unchanged** — `load_full_context()` continues calling `_parse_template` directly.

## What Did NOT Change

- `_parse_template` itself — no rename, no signature change, no behavior change
- `load_full_context()` and other internal callers in `context.py`
- The return type contract: `tuple[str, ReportTemplate | None, ContextProfile | None]`
- Test assertions and expected values — only the function name changed

## Risk Resolution

| Flagged Risk | Actual Outcome | Lesson |
|---|---|---|
| "Whether all test imports should switch to public wrapper" (brainstorm) | All 22 switched — audit confirmed all test public contract | When in doubt, audit every call site; don't assume some are "internal" |
| "Whether `parse_context_file` needs `__init__.py` export" (plan) | Exported for consistency with other context functions | Follow existing export patterns; trivially reversible if wrong |
| MCP parity lint script (planned, deferred) | Deferred — existing pytest test sufficient | Don't force two items into one cycle if one isn't ready |

## Prevention Strategies

1. **Pattern: Public wrappers for cross-module access** — When module A needs functionality from module B's private function, add a public wrapper in module B. The wrapper can be a one-line delegation. CLI entry points are the highest-priority case because they sit at the boundary between user-facing code and library internals.

2. **Detection: grep for cross-module underscore imports** — Run `grep -rn "from.*import _" research_agent/ | grep -v test` as a CI check. Any match in non-test files is a code smell worth reviewing.

3. **Process: Fix trivial coupling debt in the same cycle** — This fix was ~10 lines. It was deferred from cycle 24 to cycle 25, consuming planning/implementation/review overhead across two cycles for a five-minute change. Rule of thumb: if the fix is under 20 lines with no design ambiguity, include it in the current cycle.

4. **Process: "Fix later" notes need a size estimate** — Annotate tech debt notes with effort estimates (e.g., "~10 lines, no design decisions"). This makes triage trivial: anything under 20 lines gets bundled into housekeeping rather than becoming its own cycle.

## Cross-References

- **Predecessor:** [`swappable-context-profiles.md`](../feature-implementation/swappable-context-profiles.md) — Cycle 24, where the coupling was introduced
- **Related pattern:** [`pip-installable-package-and-public-api.md`](pip-installable-package-and-public-api.md) — Public API boundary design and validation ownership
- **Parsing edge cases:** [`defensive-yaml-frontmatter-parsing.md`](../logic-errors/defensive-yaml-frontmatter-parsing.md) — YAML parsing robustness in context files

## Three Questions

1. **Hardest pattern to extract from the fixes?** Whether "add a public wrapper" is worth documenting as a standalone pattern or is just basic encapsulation. Decided it's worth it because the prevention strategies (grep detection, size-estimate on debt notes) are more valuable than the pattern itself.
2. **What did you consider documenting but left out, and why?** The MCP parity lint script that was planned but deferred. It wasn't solved in this cycle, so documenting it here would mix "what happened" with "what didn't happen." It stays on the deferred items list.
3. **What might future sessions miss that this solution doesn't cover?** The grep detection strategy (`from.*import _`) will produce false positives for legitimate private imports in test files. A more sophisticated lint would need to distinguish test files from production code, which this doc notes but doesn't solve.
