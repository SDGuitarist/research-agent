# HANDOFF — Research Agent

**Date:** 2026-03-10
**Branch:** `main`
**Phase:** Cycle 26 — COMPLETE. Roadmap reprioritized with epistemic calibration study findings.

## Current State

Cycle 26 is fully complete. Roadmap expanded from 4 cycles (27-30) to 5 cycles (27-31) after integrating findings from an exploratory study on prompt-induced epistemic calibration. Three new features added: per-task temperature controls (C27), evidence-tier labeling (C29), pre-summary abstention gate (C30), novelty-biased decomposition (C31). MCP tools #123 promoted to C31 (deferral #2 triggers promote-or-drop). 938 tests passing.

## Key Artifacts

| Phase | Location |
|-------|----------|
| Brainstorm | `docs/brainstorms/2026-03-08-cycle-26-mcp-parity-lint-brainstorm.md` |
| Plan | `docs/plans/2026-03-08-cycle-26-mcp-parity-lint-plan.md` |
| Plan Review | `docs/reviews/2026-03-08-cycle-26-codex-plan-findings.md` |
| Code Review | `docs/reviews/2026-03-10-cycle-26-claude-code-review-findings.md` |
| Solution | `docs/solutions/workflow/mcp-parity-lint-ci-enforcement.md` |
| Entropy Roadmap | `docs/research/2026-03-09-entropy-fixes-roadmap.md` |
| PR #6 | https://github.com/SDGuitarist/research-agent/pull/6 (feature, merged) |
| PR #7 | https://github.com/SDGuitarist/research-agent/pull/7 (review fixes, merged) |

## Deferred Items

- **Tier 3 model routing** (summarization) — deferred indefinitely; epistemic calibration study reinforces prompt design > model routing for summarization
- **IDN/punycode domain matching** — known limitation in blocked_domains, acceptable
- **MCP `--cost` + `--critique-history` tools** (#123) — promoted to Cycle 31 (deferral #2, promote-or-drop applied)

## Roadmap Summary (Cycles 27-31)

| Cycle | Theme | New Items (from study) | Sessions |
|-------|-------|----------------------|----------|
| 27 | Input Validation + Generation Controls | Per-task temperature | 3 |
| 28 | Relevance & Source Quality Gates | — | 3 |
| 29 | Verification & Synthesis Integrity | Evidence-tier labeling | 4 |
| 30 | Summarization & Context Preservation | Pre-summary abstention gate | 4 |
| 31 | Research Distinctiveness | Novelty-biased decomposition + MCP tools #123 | 3 |

Key design principle from the study: **prompt semantics before generation controls**. Temperature is secondary to system prompts — bundled into C27 as a low-effort addition, not a standalone cycle.

## Three Questions

1. **Hardest decision?** Where to place evidence-tier labeling — C29 (with skeptic enforcement) vs C30 (with summarization). Chose C29 because both features shape how synthesis handles confidence, and they're two sides of the same coin.
2. **What was left out?** A standalone "epistemic controls" cycle — considered grouping all study-derived features together, but they fit better distributed across existing cycles where they share code and dependencies.
3. **Least confident about?** Pre-summary abstention gate placement (C30). 75% confidence — the mechanism is validated but whether it belongs in `summarize.py` (per-source) or `synthesize.py` (all sources visible) needs planning.

### Prompt for Next Session

```
Read HANDOFF.md for context. This is Research Agent, a Python CLI that searches the web and generates structured markdown reports with citations using Claude. Cycle 26 is complete. Roadmap reprioritized with epistemic calibration study findings. Next: start Cycle 27 (input validation + generation controls: vague query detection, idempotent sanitization, per-task temperature). Roadmap: docs/research/2026-03-09-entropy-fixes-roadmap.md.
```
