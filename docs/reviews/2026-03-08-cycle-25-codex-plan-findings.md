# Codex Plan Findings — Cycle 25 Housekeeping

## Findings

### P2 Blocker — Step 2 widens the package public API, but the plan does not include the test file that enforces that API

- Evidence: the plan explicitly adds `parse_context_file` to `research_agent/__init__.py` and `research_agent.__all__` at `docs/plans/2026-03-08-cycle-25-housekeeping-plan.md:63-68`.
- Current contract: `tests/test_public_api.py:45-66` asserts the exact contents of `research_agent.__all__`, and `parse_context_file` is not in that expected set today.
- Exact impact: if the work follows the plan mechanically, the full suite cannot stay green. `tests/test_public_api.py` will fail unless it is updated. This is also a broader API-surface decision than the plan admits in `docs/plans/2026-03-08-cycle-25-housekeeping-plan.md:153`.
- Fix before work: choose one path and write it into the plan:
- Keep `parse_context_file` module-public only. In that case, remove Step 2 and keep imports on `research_agent.context`.
- Make `parse_context_file` package-public. In that case, add `tests/test_public_api.py` to the file list, acceptance criteria, and required checks.

### P3 Advisory — The `_parse_template` audit in the plan is internally inconsistent

- Evidence: the plan says it audited "26 call sites" and says no string references exist at `docs/plans/2026-03-08-cycle-25-housekeeping-plan.md:19,26`.
- Current file state: `tests/test_context.py` has 22 `_parse_template(` call sites at `tests/test_context.py:231-1004`, plus one import reference at `tests/test_context.py:9-19`, and one class docstring reference at `tests/test_context.py:214-215`.
- Exact impact: the implementer cannot treat the audit text as fully reliable, which matters here because this cycle is supposed to be a mechanical cleanup with no fresh design decisions.
- Fix: correct the plan text to 22 call sites, then list the import and docstring references separately.

### P3 Advisory — The lint script duplicates an existing parity check without stating where the duplicate check will actually run

- Evidence: the proposed script in `docs/plans/2026-03-08-cycle-25-housekeeping-plan.md:85-133` uses the same `mcp.list_tools()` plus string-membership comparison that already exists in `tests/test_mcp_server.py:462-469`.
- Exact impact: the script may still be useful, but right now it adds a second implementation to maintain without a stated enforcement path beyond "run it manually." That weakens the justification for extra maintenance surface.
- Fix: either say explicitly that the repo wants a standalone manual fast-path and keep the script, or replace the new script with a documented focused pytest command for this existing check.

## Prior Phase Risk

> **Least confident about:** Whether all `_parse_template` test imports should switch to the public wrapper, or just the ones testing public behavior. Plan phase should audit each test.

This review partially addresses that risk: the 22 call sites are real, but the written audit overstates the count and should be corrected before work starts.

## What I Did Not Review Or Could Not Verify

- I did not run `python3 -m pytest tests/ -v`; this is a static plan review before implementation.
- I did not verify FastMCP behavior outside the current repo usage. My judgment on the lint script is based on the existing async parity test in `tests/test_mcp_server.py`, not on a separate runtime experiment.

## Suggested Fix Order

1. Resolve the `parse_context_file` API-surface decision and update the plan scope accordingly. This is the only blocker.
2. Fix the inaccurate `_parse_template` audit counts so the work can be executed mechanically.
3. Decide whether the standalone parity script is worth keeping over the existing focused pytest check, then update the plan wording to match that decision.

## Claude Code Fix Prompt

```text
Read docs/plans/2026-03-08-cycle-25-housekeeping-plan.md and docs/reviews/2026-03-08-cycle-25-codex-plan-findings.md.

Revise the plan only. Do not implement code yet.

Exact scope:
- docs/plans/2026-03-08-cycle-25-housekeeping-plan.md
- docs/reviews/2026-03-08-cycle-25-codex-plan-review-handoff.md only if you need to keep the handoff consistent with the revised plan

Required changes:
- Decide whether parse_context_file is only a public function in research_agent/context.py or a package-root public API exported from research_agent/__init__.py.
- If you keep the __init__.py export, add tests/test_public_api.py to the planned file list, acceptance criteria, and required checks, and say plainly that this is a package public API change.
- If you do not keep the __init__.py export, remove that step from the plan and keep imports scoped to research_agent.context.
- Correct the _parse_template audit so it matches the current file: 22 call sites in tests/test_context.py, plus the import reference and the class docstring reference.
- Decide whether scripts/lint_mcp_parity.py stays in scope. If it does, explain the value of the standalone script over the existing pytest parity test in tests/test_mcp_server.py. If it does not, replace it with a documented focused pytest command.

Acceptance criteria:
- The revised plan can be executed mechanically without new design decisions.
- Every file that would need to change is listed explicitly.
- Required checks cover any public API test impact.
- The plan's counts and file references match the current repo.

Stop conditions:
- Stop after updating the plan docs.
- Do not modify research_agent/, tests/, or scripts/.
```
