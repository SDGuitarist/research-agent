# Review Context — Research Agent

## Risk Chain

**Brainstorm risk:** "Whether all `_parse_template` test imports should switch to the public wrapper, or just the ones testing public behavior."

**Plan mitigation:** Audited all 26 call sites in `test_context.py`. All 22 test the public contract (string in → tuple out), none test internal implementation details. Decision: switch all.

**Work risk (from Feed-Forward):** "Whether `parse_context_file` needs to be in `__all__` / `__init__.py`. It's used by CLI (internal) and tests, not by external consumers."

**Review resolution:** 0 findings. Clean pass — 938 tests, no material issues. Exported for consistency with other context functions; trivially reversible.

## Files to Scrutinize

| File | What changed | Risk area |
|------|-------------|-----------|
| `research_agent/context.py` | Added `parse_context_file()` public wrapper | Thin delegation — low risk |
| `research_agent/cli.py` | Swapped `_parse_template` → `parse_context_file` import | Import path only |
| `tests/test_context.py` | 22 call sites switched to public wrapper | Same assertions, name change only |

## Plan Reference

`docs/plans/2026-03-08-cycle-25-housekeeping-plan.md`
