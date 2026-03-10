# Codex Plan Findings — Cycle 26 MCP Parity Lint Script + CI Workflow

## Findings

### P2 Blocker — The plan still does not include the step that makes this CI check truly enforce the merge gate

- Evidence: the brainstorm says the new workflow "actually prevents drift from reaching `main`" at `docs/brainstorms/2026-03-08-cycle-26-mcp-parity-lint-brainstorm.md:16-20`, and the handoff explicitly asks whether a required status check is needed at `docs/reviews/2026-03-08-cycle-26-codex-plan-review-handoff.md:52-53`. But the plan itself only adds `.github/workflows/mcp-lint.yml` at `docs/plans/2026-03-08-cycle-26-mcp-parity-lint-plan.md:74-105`; it does not include the repo-settings step that would make `MCP Parity Lint` required on `main`.
- Exact impact: if a developer follows the plan mechanically, they can create the workflow file but still leave the check advisory-only. That means this cycle only partially resolves the cycle 25 blocker about "enforcement path."
- Fix before work: add one explicit rollout step outside the repo files to make `MCP Parity Lint` a required status check on `main`, or narrow the plan's claim so it says "surfaces drift in CI" instead of "prevents drift from reaching main."

### P3 Blocker — The local verification path assumes tooling the plan never tells the implementer to install

- Evidence: the plan's local checks are `python scripts/lint_mcp_parity.py` and `python3 -m pytest tests/ -x -q` at `docs/plans/2026-03-08-cycle-26-mcp-parity-lint-plan.md:72,115-119`, but the only install command the plan discusses is `pip install -e .` at `docs/plans/2026-03-08-cycle-26-mcp-parity-lint-plan.md:19,67,100,137`. In this repo, test tooling lives in the optional `test` extra at `pyproject.toml:25-29`, and the repo setup doc says `pip install -e ".[test]"` at `CLAUDE.md:54-58`. The plan also says `pip install -e .` is "what the README documents," but the current README still says `pip install -r requirements.txt` at `README.md:16-22`.
- Exact impact: a developer starting from a clean checkout still has to guess which install command is required for local verification. That breaks the handoff's standard of being executable without new design decisions.
- Fix before work: add one explicit prerequisites section that separates CI/runtime install (`pip install -e .`) from local verification install (`pip install -e ".[test]"`), and keep the verification commands consistent with the repo's normal local command style.

### P3 Advisory — The Ubuntu dependency-risk text is written as if the runner packaging is already known

- Evidence: the plan says the risk is mitigated because `ubuntu-latest` "ships Python 3.12+ with lxml build deps pre-installed" at `docs/plans/2026-03-08-cycle-26-mcp-parity-lint-plan.md:26`, then repeats `apt-get install -y libxml2-dev libxslt-dev` as a fallback at `docs/plans/2026-03-08-cycle-26-mcp-parity-lint-plan.md:138`. The repo proves the Python dependencies exist at `pyproject.toml:12-22`, but it does not prove the GitHub runner image has the needed OS packages.
- Exact impact: if CI install fails, the plan points the implementer at an unverified explanation instead of stating plainly that the GitHub Actions environment still needs proof.
- Fix for plan quality: rewrite this as an unverified rollout risk, not a solved one. Keep the `apt-get` line as the first fallback if CI proves the wheel/install path is not enough.

## Prior Phase Risk

> **Least confident:** Whether `pip install -e .` on `ubuntu-latest` will succeed without additional system packages for `lxml` or `trafilatura`. If it fails in CI, the fix is adding `apt-get install -y libxml2-dev libxslt-dev` before the pip install step.

This review partially addresses that risk: import-time FastMCP registration is verified locally, but the clean GitHub Actions install path is still unverified and should remain explicit in the plan.

## What I Did Not Review Or Could Not Verify

- I did not run a live GitHub Actions job or inspect GitHub branch-protection settings, so I cannot confirm whether a new `MCP Parity Lint` workflow would block merges today.
- I did not test `pip install -e .` from a clean `ubuntu-latest` runner, so I cannot confirm whether extra OS packages are needed there.
- I did verify the current repo behavior locally: `python3 -m pytest tests/ -x -q` passed with 938 tests, `python3 -m pytest tests/test_mcp_server.py -q` passed with 40 tests, and importing `research_agent.mcp_server` without API keys still registered 7 tools.

## Suggested Fix Order

1. Add the missing branch-protection rollout step, or narrow the enforcement claim so the plan no longer overstates what the workflow file alone achieves.
2. Add explicit local-versus-CI setup prerequisites so the verification steps are runnable from a clean checkout.
3. Reword the Ubuntu dependency-risk section so it clearly separates what is verified locally from what still must be proven in GitHub Actions.

## Claude Code Fix Prompt

```text
Read docs/plans/2026-03-08-cycle-26-mcp-parity-lint-plan.md and docs/reviews/2026-03-08-cycle-26-codex-plan-findings.md.

Revise the plan docs only. Do not implement code yet.

Exact scope:
- docs/plans/2026-03-08-cycle-26-mcp-parity-lint-plan.md
- docs/brainstorms/2026-03-08-cycle-26-mcp-parity-lint-brainstorm.md only if needed to keep the enforcement wording consistent
- docs/reviews/2026-03-08-cycle-26-codex-plan-review-handoff.md only if needed to keep the handoff aligned with the revised plan

Required changes:
- Add an explicit rollout step for making `MCP Parity Lint` a required status check on `main`, or rewrite the goal so it only claims CI visibility instead of merge-blocking enforcement.
- Add one clear prerequisites/setup section that separates CI install (`pip install -e .`) from local verification install (`pip install -e ".[test]"`).
- Make the local verification commands runnable from a clean checkout without guessing which install path or Python command to use.
- Rewrite the Ubuntu dependency-risk text so it is clearly marked as unverified rather than assuming runner system packages.
- Keep scope limited to docs. Do not add or change `scripts/`, `.github/workflows/`, `research_agent/`, or `tests/`.

Acceptance criteria:
- A developer can follow the revised plan without guessing environment setup or rollout steps.
- The plan makes a clear distinction between advisory CI visibility and required merge protection, or it includes the required-status-check step explicitly.
- The risk section clearly separates what is verified locally from what still must be proven in GitHub Actions.
- The file list and required checks still match the current repo.

Required checks:
- Re-read `CLAUDE.md`, `pyproject.toml`, and `README.md` while revising the setup text.
- Keep the current parity-test reference to `tests/test_mcp_server.py:462-469`.
- Stop after updating docs only.
```

## Three Questions

1. **Hardest judgment call in this review?** Whether the missing required-status-check step is a blocker or only an advisory. I treated it as a blocker because this cycle's whole justification is "enforcement," not just visibility.
2. **What did you consider flagging but chose not to, and why?** I considered flagging the duplicated parity logic between the script and `tests/test_mcp_server.py`, but I left it out as a finding because the rule is tiny and the real missing piece is enforcement, not deduplication.
3. **What might this review have missed?** A live GitHub Actions run could still reveal an environment-specific packaging problem or an existing branch-protection rule that changes how serious the enforcement gap is.
