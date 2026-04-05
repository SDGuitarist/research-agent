# Cycle 27 Review Summary — Input Validation & Generation Controls

**Date:** 2026-04-05
**Branch:** `main`
**Commits:** `ddc4d84..77c1011` (4 implementation commits + 1 review-fix commit)
**Files changed:** 28 (1,247 added / 116 removed)
**Tests:** 955 passing

## Severity Snapshot

- P1 (Critical): 0
- P2 (Important): 3
- P3 (Nice-to-have): 2

## Review Agents Used

| Agent | Key Finding |
|-------|-------------|
| kieran-python-reviewer | 1 P2: temperature misclassification on `generate_insufficient_data_response` |
| security-sentinel | 1 P2: missing prompt injection regression test. 3 low findings (all acceptable). |
| performance-oracle | No concerns. `html.unescape` adds sub-microsecond overhead per call. |
| architecture-strategist | All changes architecturally sound. Follows Cycle 21 model routing pattern. |
| code-simplicity-reviewer | No YAGNI violations. VagueQueryResult is slightly heavy but has test ergonomic benefit. |
| agent-native-reviewer | 1 P2 + 2 P3: MCP standalone tools use wrong temperature, temperature invisible in mode listing, vague query undocumented in instructions. |
| learnings-researcher | 6 relevant past solutions found. Sanitization fix addresses documented bug. |

## Recommended Fix Order

| # | Issue | Priority | Why this order | Unblocks |
|---|-------|----------|---------------|----------|
| 1 | 127 - insufficient data response temperature misroute | P2 | 1-line fix, aligns all call sites to correct tier | -- |
| 2 | 128 - missing prompt injection regression test | P2 | Security regression risk; 15-line test addition | -- |
| 3 | 129 - MCP standalone tools temperature defaults | P2 | 2-line fix, closes agent parity gap | 130 |
| 4 | 130 - temperature invisible in list_research_modes | P3 | Makes Cycle 27 feature visible to MCP agents | -- |
| 5 | 131 - vague query hint in MCP instructions | P3 | 1-line docs addition | -- |

## Cross-Agent Convergence

- **Sanitization is correct:** Security + architecture + performance all confirmed the `html.unescape()`-then-escape pattern is sound, idempotent, and has negligible overhead.
- **Temperature threading is consistent:** Architecture + simplicity + Python reviewer all validated the per-param pattern matches Cycle 21 precedent. No YAGNI violation.
- **Vague query gate is well-placed:** Architecture confirmed fail-fast placement. Security confirmed the gate is not a security boundary (cost protection only). Simplicity confirmed no unnecessary abstraction.
- **MCP parity is the main gap:** Agent-native reviewer found 3 issues, all small fixes. The temperature feature works internally but is partially invisible at the MCP boundary.

## Institutional Knowledge Applied

The learnings researcher surfaced:
- `docs/solutions/security/non-idempotent-sanitization-double-encode.md` — the exact bug this cycle fixes
- `docs/solutions/security/context-path-traversal-defense-and-sanitization.md` — input validation at boundaries pattern
- Cycle 21 parameter threading pattern — confirmed temperature follows the same approach
- Epistemic calibration study — temperature is style not epistemic; confirmed the design principles are applied

## Stale Documentation

- `MEMORY.md` Cycle 20 note says "`sanitize_content` is NOT idempotent" — now incorrect. Should be updated during compound phase.

## Three Questions

1. **Hardest judgment call in this review?** Whether the MCP standalone tool temperature defaults (#129) are a genuine P2 or an accepted limitation. The plan explicitly documented that "MCP tools don't have a mode object" and accepted 1.0 defaults. But the agent-native reviewer correctly identified that hardcoded sensible defaults (0.2/0.8) are a 2-line fix that closes a real behavioral gap. Elevated to P2.

2. **What did you consider flagging but chose not to?** The `VagueQueryResult` dataclass being heavier than a direct raise. Both simplicity and Python reviewers noted this but agreed the test ergonomic benefit (asserting `result.is_valid` vs `pytest.raises`) justifies the pattern. Not worth a todo.

3. **What might this review have missed?** The `test_mcp_server.py` tests couldn't be verified (missing `fastmcp` dependency, noted in HANDOFF.md). If MCP server code has implicit assumptions about error message format that the new `VagueQueryError` messages violate, those would only surface in integration testing.
