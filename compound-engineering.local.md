# Review Context — Research Agent

## Risk Chain

**Brainstorm risk:** "Whether the GitHub Actions workflow will work correctly on first try — Python version, dependency installation, and whether fastmcp tools register at import time."

**Plan mitigation:** Verified locally that `@mcp.tool` decorators register at import time — no server startup needed. Documented `pip install -e .` as install method matching local dev. Identified `apt-get install libxml2-dev` as fallback if CI runner lacks system packages.

**Work risk (from Feed-Forward):** "Whether `pip install -e .` on ubuntu-latest will succeed without additional system packages."

**Review resolution:** 8 findings (0 P1, 6 P2, 2 P3) from 6 agents. Top finding: substring matching false-positive risk (#122, 3 agents converged). FastMCP version blocker caught by Codex review and fixed. CI passed on first run — the flagged risk was a non-issue.

**Compound lesson:** Import-time registration is a FastMCP design guarantee. Document framework behavior assumptions in plans so they don't block future cycles.

**Roadmap reprioritization (2026-03-10):** Integrated findings from epistemic calibration study. Three design principles added: (1) prompt semantics before generation controls, (2) upstream fixes before downstream, (3) epistemic friction over blanket refusal. Roadmap expanded from 4 to 5 cycles, 3 new features added.

## Files to Scrutinize

| File | What changed | Risk area |
|------|-------------|-----------|
| `.github/workflows/mcp-lint.yml` | New CI workflow with SHA-pinned actions | First real CI workflow — verify runner compatibility |
| `scripts/lint_mcp_parity.py` | Word-boundary regex matching | False positives on tool names with regex special chars |
| `research_agent/mcp_server.py` | Workflow guidance sentence in instructions | Instructions string is source of truth for agent behavior |
| `tests/test_mcp_server.py` | Updated matching logic | Test mirrors lint script — must stay in sync |
| `pyproject.toml` | FastMCP pinned to `>=3.0,<3.1` | Version constraint prevents untested breaking changes |

## Deferred Items Tracking

| Item | Deferral Count | Rule |
|------|---------------|------|
| MCP `--cost` + `--critique-history` tools (#123) | 2 | Promoted to Cycle 31 (promote-or-drop applied) |

## Epistemic Calibration Study — Key Findings for Review

These findings from an exploratory study inform how new features should be reviewed:

1. **Temperature is a style knob, not an epistemic knob** — review should not expect temperature changes to fix hallucination. System prompts do the epistemic work.
2. **Evidence-tier labeling reduces overclaiming** — when the model must label claims as documented/inference/illustrative/speculative, it becomes more disciplined. Review synthesis prompts for this pattern.
3. **Skeptical system prompts create epistemic friction without over-refusal** — the model can refuse fabricated citations while still accurately summarizing real papers. Review skeptic enforcement for this balance.
4. **Abstention gates need upstream filters** — pre-summary abstention works best when sources have already passed quality checks. Without upstream filters, expect false refusals.

## Plan Reference

`docs/plans/2026-03-08-cycle-26-mcp-parity-lint-plan.md`
Entropy roadmap (cycles 27-31): `docs/research/2026-03-09-entropy-fixes-roadmap.md`
