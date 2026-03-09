# Brainstorm: Housekeeping — MCP Parity Lint + Public parse_context_file (Cycle 25)

**Date:** 2026-03-08
**Status:** Complete
**Prior deferred items:** MCP parity lint (Cycles 19, 20, 22), `_parse_template` public wrapper (Cycle 24)

## What We're Building

Two small, independent improvements that resolve long-standing deferred items:

### Item 1: MCP Parity Lint Script

**Problem:** The MCP instructions string in `mcp_server.py` is manually maintained. A pytest test (`test_all_tools_mentioned_in_instructions`) catches drift, but only after you run the full test suite. There's no fast feedback loop (pre-commit hook or standalone script) to catch it before committing.

**Solution:** A standalone lint script that:
1. Imports the MCP server's `mcp` object
2. Compares registered `@mcp.tool` function names against the instructions string
3. Exits non-zero if any tool is missing from instructions
4. Can run as a pre-commit hook or CI check

**Where it lives:** `scripts/lint_mcp_parity.py` — simple, single-purpose, no dependencies beyond the project itself.

### Item 2: Public `parse_context_file()` Wrapper

**Problem:** `cli.py` imports `_parse_template` (a private function) from `context.py` for the `--list-contexts` feature. This creates coupling to an internal implementation detail.

**Solution:** Add a public `parse_context_file()` function in `context.py` that wraps `_parse_template()`. Update `cli.py` to import the public function instead.

## Why These Two Together

Both are:
- Small (~30-50 lines each of new/changed code)
- Independent (no shared state or ordering dependency)
- Resolving deferred items that have been carried forward across multiple cycles
- Low risk — no pipeline behavior changes, no new dependencies

Bundling them into one housekeeping cycle avoids the overhead of separate brainstorm/plan/review loops for trivial changes.

## Key Decisions

### 1. Standalone script, not a pytest plugin or custom linter framework

**Why:** A Python script in `scripts/` is the simplest thing that works. It can be run manually (`python scripts/lint_mcp_parity.py`), added to a Makefile target, or wired into pre-commit. No framework, no configuration, no dependencies.

**Rejected:** pytest plugin (already have the test — this is about fast standalone checking), ruff custom rule (overkill for one check), CI-only (want local feedback too).

### 2. Script checks instructions string, not docstrings or parameter schemas

**Why:** The existing gap is specifically "are all tool names mentioned in the instructions string?" That's what the deferred item tracks. Parameter schema validation or docstring quality are separate concerns — YAGNI.

### 3. `parse_context_file()` is a thin wrapper, not a new API

**Why:** The function signature and return type stay identical to `_parse_template()`. It's literally `return _parse_template(raw)`. The value is in making the import path public and stable, not in adding new behavior.

**Rejected:** Returning a richer object (NamedTuple, dataclass) — would change the call site in `cli.py` and every test. Not worth it for a coupling fix.

### 4. Keep `_parse_template` as the internal implementation

**Why:** `parse_context_file()` delegates to `_parse_template()`. Internal callers (`load_full_context`) continue using `_parse_template()` directly. No refactoring of existing internal code paths.

### 5. Tests import the public wrapper, not the private function

**Why:** Tests in `test_context.py` that currently import `_parse_template` should switch to `parse_context_file` — they're testing the public API. This also validates that the wrapper works correctly.

**Rejected:** Leaving test imports as-is (misses the point of having a public API).

## Scope Boundaries

**In scope:**
- `scripts/lint_mcp_parity.py` — standalone lint script
- `context.py` — add `parse_context_file()` public wrapper
- `cli.py` — switch import from `_parse_template` to `parse_context_file`
- `test_context.py` — switch imports to public wrapper
- `__init__.py` — export `parse_context_file` if context functions are already exported

**Out of scope:**
- Pre-commit hook configuration (user can wire it up themselves)
- CI pipeline changes
- Removing the existing pytest parity test (it stays as a safety net)
- Changing `_parse_template` signature or behavior
- Adding new MCP tools or changing the instructions string content
- Renaming `_parse_template` itself

## Integration Points

| Change | File | Impact |
|--------|------|--------|
| New lint script | `scripts/lint_mcp_parity.py` | Standalone, no imports from it |
| Public wrapper | `context.py` | New export, delegates to existing private function |
| CLI import fix | `cli.py` | Swap one import name, no behavior change |
| Test import fix | `test_context.py` | Swap import names, same assertions |

## Risk Assessment

**Very low.** Both items are mechanical refactors with no behavior changes. The lint script is additive (new file). The wrapper is a thin delegation. The import swaps are name changes only.

The only thing that could go wrong: missing an import site. The plan phase should list every `_parse_template` import exhaustively.

## Feed-Forward

- **Hardest decision:** Whether to also wire the lint script into pre-commit hooks or CI. Decided to keep it manual — the script exists, users can wire it however they want. Avoids scope creep into CI configuration.
- **Rejected alternatives:** pytest plugin for the lint (already have the test), richer return type for `parse_context_file` (unnecessary refactoring), removing `_parse_template` entirely (internal callers still use it).
- **Least confident:** Whether all `_parse_template` test imports should switch to the public wrapper, or just the ones that test "public behavior." The plan phase should audit each test to decide — some tests might be specifically testing internal parsing edge cases that belong on the private function.
