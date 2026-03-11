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

## Security Review Session — 2026-03-11

### What Was Done

- Performed a repo-grounded security review of fetch/SSRF, prompt construction, context loading, report storage, critique-history loading, and MCP boundaries.
- Ran the full test suite: `python3 -m pytest tests/ -q` → `938 passed`.
- Wrote the review document at `docs/reviews/2026-03-11-codex-security-review.md`.
- Wrote the Claude Code fix handoff at `docs/reviews/2026-03-11-claude-code-security-fix-handoff.md`.

## Three Questions

1. Hardest judgment call in this session?
How to calibrate the symlink findings for a repo that is mostly a local CLI. The code clearly intends repo-local containment, but the default deployment model lowers the practical severity.

2. What did you consider flagging but left out, and why?
I did not elevate the programmatic `mcp` object exposure to a primary finding because the shipped `research-agent-mcp` entrypoint already enforces loopback-only HTTP binding.

3. Least confident about going into the next phase?
Whether the project intentionally relies on symlinked `contexts/` or `reports/` roots in any local workflow. The fixes should stop and document that if it turns out to be an intentional pattern.

### Prompt for Next Session

```
Read docs/reviews/2026-03-11-codex-security-review.md and docs/reviews/2026-03-11-claude-code-security-fix-handoff.md. Implement the confirmed security fixes in the scoped files only, run the listed tests, and stop if symlink-hardening would break an intentional repo workflow.
```

## Security Fix Implementation — 2026-03-11

### What Was Done

- Implemented the confirmed security fixes from the 2026-03-11 review.
- Hardened prompt construction so untrusted URL strings are sanitized before entering summarize/synthesize XML prompts.
- Hardened `contexts/` handling so discovery, auto-detect, preview, and explicit context loading do not follow symlinks outside the literal repo-local `contexts/` root.
- Hardened `reports/` and `reports/meta/` handling so auto-save, MCP report retrieval, and critique-history loading do not follow symlinks outside the literal repo-local roots.
- Hardened cascade fallback so URLs whose hostnames resolve to private/internal IPs are not forwarded to Jina Reader or Tavily Extract.
- Closed the remaining CLI gap in `--list-contexts` so it now uses the hardened context helpers instead of reading `contexts/` directly.
- Added regression tests for prompt URL injection, symlinked contexts, symlinked reports roots, symlinked critique-history files, private-resolving hostnames in cascade fallback, and CLI `--list-contexts`.
- Ran `python3 -m pytest tests/test_main.py tests/test_context.py tests/test_mcp_server.py tests/test_summarize.py tests/test_synthesize.py tests/test_cascade.py -q` → `303 passed`.
- Ran `python3 -m pytest tests/ -q` → `948 passed`.

### Residual Caveat

- The hardening intentionally rejects symlinked `reports/` and `contexts/` roots that point outside the repo-local directories. I did not find repo docs indicating that this is an intended workflow, but if a local setup depends on it, standard/deep auto-save and explicit context selection will now fail closed instead of following the symlink.

### Prompt for Next Session

```
Read HANDOFF.md and docs/reviews/2026-03-11-codex-security-review.md. The confirmed security fixes are implemented and 948 tests pass. If more security work is needed, focus on secondary hardening or documentation only; do not reopen the fixed prompt-sanitization, context-symlink, reports-symlink, or cascade-forwarding issues unless a regression is found.
```
