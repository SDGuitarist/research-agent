# HANDOFF — Research Agent

**Date:** 2026-04-05
**Branch:** `main`
**Phase:** Cycle 27 — Work COMPLETE (all 3 sessions). Ready for Review.

## Current State

All 3 sessions implemented and committed:
- Session 1: Idempotent sanitization via `html.unescape()` normalization
- Session 2: Vague query detection gate (`check_query_vagueness` + `VagueQueryError`)
- Session 3: Per-task temperature controls (3 fields on `ResearchMode`, threaded to 16 API call sites across 10 modules)

941 tests passing. 6 commits on main ahead of origin.

## Key Artifacts

| Phase | Location |
|-------|----------|
| Brainstorm | `docs/brainstorms/2026-04-05-cycle-27-input-validation-brainstorm.md` |
| Plan | `docs/plans/2026-04-05-cycle-27-input-validation-plan.md` |
| Session 1 | `fix(27-1): make sanitize_content idempotent via unescape-then-escape` |
| Session 2 | `feat(27-2): add vague query detection gate` |
| Session 3 | `feat(27-3): add per-task temperature controls to ResearchMode` |

## Deferred Items

- **Tier 3 model routing** (summarization) — deferred indefinitely
- **IDN/punycode domain matching** — known limitation, acceptable
- **MCP `--cost` + `--critique-history` tools** (#123) — Cycle 31

## Three Questions

1. **Hardest implementation decision?** How to handle the `evaluate_sources` → `score_source` temperature plumbing. `evaluate_sources` already takes a `mode: ResearchMode` param, so rather than adding a redundant `temperature` param, we read `mode.planning_temperature` internally and pass it to `score_source` in the closure. This keeps the API clean but is a slight deviation from the "pass temperature alongside model" pattern used everywhere else.
2. **What did you consider changing but left alone?** Considered making mock_score functions in test_relevance.py accept `**kwargs` instead of adding `temperature=None` explicitly. Left alone — explicit params are clearer and match the real function signature. The 18 mock updates were mechanical.
3. **Least confident about going into review?** The MCP server's `critique_report` and `generate_followups` tools call module functions directly without going through agent.py. They use the `temperature: float = 1.0` default, meaning they get API-default temperature rather than the tuned values. This is intentional (MCP tools don't have a mode object) but worth flagging for the reviewer.

### Prompt for Next Session

```
Read HANDOFF.md. Cycle 27 work is complete (3 sessions, 3 commits). Next: run Codex Code Review handoff. Branch: main. Plan: docs/plans/2026-04-05-cycle-27-input-validation-plan.md. Feed-Forward risk: wrapper chain mock breakage (confirmed and fixed — 18 mock_score signatures updated in test_relevance.py).
```

### Codex Code Review Handoff

```
Review branch main (last 3 commits) against docs/plans/2026-04-05-cycle-27-input-validation-plan.md.

Focus on:
1. Does the diff match the plan? Flag anything added or missing.
2. Bugs, regressions, or missing edge cases
3. Security risks (input validation, injection, auth)
4. The Feed-Forward risk from the plan: "The 3-deep wrapper chains for summarization and 4-deep skeptic chain. Each level needs a temperature param added and forwarded. Existing tests that mock at intermediate boundaries may need their mock call expectations updated to include temperature=."
5. Files that should NOT have changed but did

Key files changed: research_agent/sanitize.py, research_agent/query_validation.py, research_agent/errors.py, research_agent/modes.py, research_agent/results.py, research_agent/agent.py, research_agent/summarize.py, research_agent/skeptic.py, research_agent/synthesize.py, research_agent/relevance.py, research_agent/decompose.py, research_agent/context.py, research_agent/search.py, research_agent/coverage.py, research_agent/iterate.py, research_agent/critique.py, research_agent/__init__.py, tests/test_sanitize.py, tests/test_query_validation.py, tests/test_agent.py, tests/test_relevance.py
Plan doc: docs/plans/2026-04-05-cycle-27-input-validation-plan.md
PR: not yet created

Output: findings ordered by severity + a Claude Code fix prompt that MUST
instruct Claude Code to:
1. Apply the requested fixes
2. Run a second review of its own changes after the fixes
3. Report any remaining risks before the task is considered complete
```
