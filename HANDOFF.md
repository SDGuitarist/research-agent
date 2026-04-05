# HANDOFF — Research Agent

**Date:** 2026-04-05
**Branch:** `main`
**Phase:** Cycle 27 — Plan REVISED after Codex review. Ready for Work.

## Current State

Cycle 27 plan revised based on Codex review findings. Key fixes: (1) Session 1 now documents the `test_ampersand_before_angle_brackets` test that must change, (2) Session 3 call-site inventory rebuilt from actual codebase — 16 API calls across 10 modules, correct function names, includes missed `generate_insufficient_data_response`, (3) wrapper chain plumbing documented for summarize (3-deep), skeptic (4-deep from agent.py), and relevance (mode object reads internally), (4) Feed-Forward updated — real risk is wrapper chain mock breakage, not auto_detect_context. 948 tests passing.

## Key Artifacts

| Phase | Location |
|-------|----------|
| Brainstorm | `docs/brainstorms/2026-04-05-cycle-27-input-validation-brainstorm.md` |
| Plan | `docs/plans/2026-04-05-cycle-27-input-validation-plan.md` |
| Entropy Roadmap | `docs/research/2026-03-09-entropy-fixes-roadmap.md` |

## Deferred Items

- **Tier 3 model routing** (summarization) — deferred indefinitely
- **IDN/punycode domain matching** — known limitation, acceptable
- **MCP `--cost` + `--critique-history` tools** (#123) — Cycle 31

## Three Questions

1. **Hardest decision?** Whether to add a `temperature` param to every module function vs. passing the entire mode object. Chose per-param to match Cycle 21 convention and avoid coupling.
2. **What was rejected?** Passing entire ResearchMode to every function (too much coupling), `html.escape()` for idempotency (also not idempotent), global temperature constants (violates dataclass convention), exporting VagueQueryError from `__init__.py` (no concrete caller needs it).
3. **Least confident about?** The 3-deep wrapper chains for summarization and 4-deep skeptic chain. Mechanical to implement, but existing tests mocking at intermediate boundaries may need mock call expectations updated to include `temperature=`.

### Prompt for Next Session

```
Read docs/plans/2026-04-05-cycle-27-input-validation-plan.md. Implement Session 1: Idempotent Sanitization. Relevant files: research_agent/sanitize.py, tests/test_sanitize.py. Do only Session 1 — commit and stop.
```
