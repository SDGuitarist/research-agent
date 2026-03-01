# Batch 3: Cleanup + Polish (096, 097, 098, 099)

**Commit:** `96e3fe2`
**Files changed:** `research_agent/mcp_server.py`, `tests/test_mcp_server.py`, `pyproject.toml`

### Fixes Applied

**096 — Remove redundant TestValidateReportFilename (P3)**
- Removed the 7-test class (43 lines) — 5 tests duplicated by `TestGetReport` integration tests
- Migrated the unique `test_long_filename_rejected` to `TestGetReport`
- Removed unused `_validate_report_filename` import from test file
- Net: -4 tests (7 removed, 3 added across this + other batches), zero coverage regression

**097 — Context parameter defensive normalization (P3)**
- Added 3-line normalization block: strips whitespace, converts `"null"` and `""` to `None`
- The string `"none"` is preserved (it means "skip context" in the three-way behavior)
- Added 2 tests: `test_context_null_string_normalized_to_none` and `test_context_none_string_preserves_skip`

**098 — Enrich MCP instructions field (P3)**
- Expanded from 1 sentence to 5, mentioning all 6 tools and the recommended workflow
- Preserved the "Set 'cwd'" instruction

**099 — Tighten fastmcp version constraint (P3)**
- Changed from `>=2.0,<4.0` to `>=2.0,<3.0`
- Prevents silent breakage on FastMCP 3.x

## Three Questions

1. **Hardest fix in this batch?** Context normalization (097). The three-way behavior (`None`/`"none"`/`"<name>"`) means normalization must be careful — `"none".lower()` stays as `"none"` which is correct, but `"None".lower()` would become `"none"` which is wrong (it should become `None`). The solution is to check for `"null"` specifically, not case-normalize to `"none"`.

2. **What did you consider fixing differently, and why didn't you?** For 097, considered also normalizing `"None"` (capital N) to Python `None`. Decided against it because MCP parameters are JSON-typed — a JSON `null` arrives as Python `None`, so `"None"` as a string is already unusual. Normalizing `"null"` covers the common LLM mistake. Adding `"None"` normalization would mask a client bug.

3. **Least confident about going into the next batch or compound phase?** The test count. We went from 802→806→802 tests across the three batches (added 8 new tests, removed 7 redundant). The net +0 might look like we lost coverage, but integration tests at the tool level are strictly more valuable than the unit tests they replaced.
