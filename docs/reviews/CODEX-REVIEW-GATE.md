# Codex Review Gate — Research Agent

Use this before merge or before asking Claude Code to fix review findings.

## Read First

- `HANDOFF.md`
- `CLAUDE.md`
- the relevant file in `docs/plans/`
- the matching file in `docs/reviews/` or `docs/solutions/` if the same area was touched before

## Compare Against

- Base branch: `main` unless the user or repo docs say otherwise

## Always Check

- Public result shapes stay consistent across the CLI, Python package API, MCP server, and saved reports.
- New HTTP, fetch, or extraction paths preserve SSRF protection, sanitization, and prompt-injection defenses.
- Model-routing or mode changes update all dependent surfaces and tests.
- Generated output in `reports/` is treated as output, not as source-of-truth code or config.
- Context, gap, or state changes preserve additive behavior and rollback safety.
- Test gaps and skipped live-integration verification are stated explicitly.

## Required Checks

- Run `python3 -m pytest tests/ -v`.
- If result models, `mcp_server`, or public APIs changed: verify backward compatibility and agent-native parity.
- If network, fetch, search, or extraction code changed: verify safety helpers stay on the path to every network call.
- If docs or generated reports changed without code changes: confirm whether the change is intentional and low risk.

## Findings Priorities

1. Safety regressions, SSRF risk, or prompt-injection exposure
2. Incorrect results, broken reports, or incompatible public API changes
3. MCP parity drift or mode-routing mismatches
4. Missing tests around new behavior or skipped verification
