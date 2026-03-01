# Batch 2: Test + Validation + Agent Parity (092, 093, 094, 095)

**Commit:** `d68c72c`
**Files changed:** `research_agent/mcp_server.py`, `tests/test_mcp_server.py`

### Fixes Applied

**092 — Auto-save test assert gap (P2)**
- Added `mock_write.assert_called_once_with(save_path, "# Saved Report")` to `test_auto_saves_standard_mode`
- Closes the feed-forward risk from work Session 3: "Whether test coverage is sufficient for the auto-save path"

**093 — Mode validation at MCP boundary (P2)**
- Added `VALID_MODES = {"quick", "standard", "deep"}` constant
- Early `ToolError` before any pipeline code executes
- Updated test to not need mocking (validation is now at the boundary)

**094 — Missing critique_report MCP tool (P2)**
- New `critique_report(filename)` tool wrapping `critique_report_file` public API
- Reuses `_validate_report_filename` for path security
- Returns formatted scores, weaknesses, suggestions
- Added `TestCritiqueReport` with happy path and error path tests

**095 — Missing skip_critique + max_sources params (P2)**
- Added `skip_critique: bool = False` and `max_sources: int | None = None` to `run_research` signature
- Pass-through to `run_research_async`
- Added `TestRunResearchParams` with tests for both parameters

## Three Questions

1. **Hardest fix in this batch?** The critique_report tool (094). Had to decide where to instantiate the `Anthropic` client — creating it inside the tool function (deferred import pattern) is consistent with the other tools but means the mock path in tests needs to patch `research_agent.critique_report_file` rather than the Anthropic constructor.

2. **What did you consider fixing differently, and why didn't you?** For 093, considered using `Literal["quick", "standard", "deep"]` type annotation instead of a runtime check. FastMCP might validate it at the schema level, but since we can't guarantee all MCP clients respect type annotations, an explicit runtime check is defense-in-depth.

3. **Least confident about going into the next batch or compound phase?** The critique_report tool's `except Exception` catch-all. It follows the same justified pattern as run_research (server boundary), but adds another place where unexpected errors are swallowed. If critique_report_file changes its exception types in the future, errors would be silently caught.
