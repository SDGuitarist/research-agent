# Codex Findings — Cycle 24: Swappable Context Profiles

**Date:** 2026-03-06
**Branch:** `main`
**Commit range:** `201b012..e3667f7`
**Pytest:** `920 passed in 130.93s`

### Prior Phase Risk

> "The `_parse_template` import in `cli.py` — it's a private function (`_` prefix). Works fine but review should confirm this is acceptable or if a thin public wrapper is warranted."

Accepted. I did not flag the private import as a finding because it is a maintainability concern, not a current correctness or safety bug.

## Findings

### P2 — Blocker
**Blocked domains still influence quick/standard query refinement before they are filtered.**

- File + line: `research_agent/agent.py:587`
- File + line: `research_agent/agent.py:951`
- Why this matters: blocked results are filtered only inside `_fetch_extract_summarize()`, but quick/standard mode builds `seen_urls` and `snippets` from `pass1_results` before that. A blocked domain can still shape `refine_query()`, which means the final report can be steered by a source the user explicitly blocked.
- Recommended fix: apply blocked-domain filtering before `seen_urls` and `snippets` are built in `_research_with_refinement()`, or add one agent-level search wrapper that filters immediately after each search call and before any refinement logic.

### P2 — Advisory
**`--list-contexts` hides malformed frontmatter as if the file simply had no profile fields.**

- File + line: `research_agent/cli.py:220`
- File + line: `research_agent/context.py:76`
- File + line: `research_agent/context.py:180`
- Why this matters: `_parse_template()` never raises on YAML or template errors; it logs a warning and returns `None` values. `cli.py` only prints `(parse error)` on `OSError`, so a broken context file is displayed as `no profile fields`, which is misleading for a discovery command.
- Recommended fix: add a thin public helper that returns parsed data plus parse status, or teach `--list-contexts` to distinguish "empty/no profile" from "frontmatter parse failed".

### P3 — Advisory
**Custom free-text tone is sanitized twice.**

- File + line: `research_agent/context.py:121`
- File + line: `research_agent/synthesize.py:59`
- Why this matters: `synthesis_tone` is sanitized at parse time and sanitized again in `_build_tone_instruction()`. Custom text containing `&`, `<`, or `>` will be double-escaped and arrive in the prompt mangled.
- Recommended fix: sanitize custom tone in one place only. The simplest fix is to treat `synthesis_tone` as already sanitized once it reaches `synthesize.py`.

### P3 — Advisory
**The new behavior still has effectively no focused regression coverage.**

- File + line: `tests/test_context.py:231`
- File + line: `research_agent/agent.py:478`
- File + line: `research_agent/agent.py:587`
- File + line: `research_agent/synthesize.py:53`
- File + line: `research_agent/cli.py:211`
- Why this matters: the full suite passes, but the only touched test file just updates `_parse_template()` tuple unpacking. There are still no targeted tests for blocked-domain filtering in quick/standard refinement, gap-schema fallback setting `self.schema_path`, tone injection/single-sanitize behavior, or `--list-contexts` parse-error reporting.
- Recommended fix: add focused tests in `tests/test_agent.py`, `tests/test_search.py`, `tests/test_synthesize.py`, and `tests/test_context.py` before treating this feature as review-complete.

## What I Did Not Review Or Could Not Verify

- I did not run live Anthropic or Tavily calls. This review used local code inspection plus the full unit/integration-style test suite.
- I did not run a live MCP client session. MCP parity was reviewed by reading the code paths, not by driving the server interactively.

## Suggested Fix Order

1. Fix the blocked-domain leak into quick/standard query refinement.
2. Make `--list-contexts` report malformed frontmatter honestly.
3. Remove double-sanitization for free-text tone.
4. Add focused regression tests for the new code paths.

## Claude Code Fix Prompt

```text
Read docs/plans/2026-03-06-feat-swappable-context-profiles-plan.md. Read docs/reviews/2026-03-06-cycle-24-codex-findings.md.

Fix only the review findings from the Codex review.

Scope:
- research_agent/agent.py
- research_agent/cli.py
- research_agent/context.py
- research_agent/synthesize.py
- tests/test_agent.py
- tests/test_context.py
- tests/test_search.py
- tests/test_synthesize.py

Required fixes:
1. Blocked domains must not influence quick/standard `refine_query()` input.
2. `--list-contexts` must distinguish malformed frontmatter from files that simply have no profile fields.
3. Free-text `synthesis_tone` must be sanitized exactly once.
4. Add focused regression tests for the above behavior plus gap-schema fallback setting `self.schema_path`.

Acceptance criteria:
- A blocked result is removed before `seen_urls` and `snippets` are built for quick/standard refinement.
- A malformed context file is shown clearly as a parse error in `--list-contexts`.
- Custom tone text containing `&` or `<` is not double-escaped in the synthesis prompt.
- `python3 -m pytest tests/ -v` passes.

Stop after the fixes, tests, and HANDOFF.md update. Do not broaden scope.
```
