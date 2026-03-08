# Codex Review Handoff — Cycle 24: Swappable Context Profiles

## Read First

1. `HANDOFF.md` — current state, all 4 sessions done
2. `CLAUDE.md` — repo conventions and test commands
3. `docs/reviews/CODEX-REVIEW-GATE.md` — review checklist for this repo
4. `docs/plans/2026-03-06-feat-swappable-context-profiles-plan.md` — v3 deepened plan with exact line numbers and security constraints

## What Changed

4 commits on `main` implementing swappable context profiles — new YAML frontmatter fields on context files that affect pipeline behavior.

| Commit | Session | Summary |
|--------|---------|---------|
| `139e3a8` | 1 | `ContextProfile` frozen dataclass + per-field YAML parsing |
| `16aead3` | 2 | `filter_blocked_urls()` + single call site in `_fetch_extract_summarize()` |
| `0d267b2` | 3 | `TONE_PRESETS` + `_build_tone_instruction()` + tone injection in synthesis |
| `e3667f7` | 4 | Gap schema fallback + `--list-contexts` CLI flag |

## Files Changed

- `research_agent/context_result.py` — new `ContextProfile` dataclass
- `research_agent/context.py` — profile field extraction in `_parse_template()`
- `research_agent/search.py` — `filter_blocked_urls()` helper
- `research_agent/agent.py` — blocked filter call, gap_schema fallback, tone threading
- `research_agent/synthesize.py` — `TONE_PRESETS`, `_build_tone_instruction()`, tone params on `synthesize_report()` and `synthesize_final()`
- `research_agent/cli.py` — `--list-contexts` flag, imports `_parse_template`

## Diff Command

```bash
git diff 201b012..e3667f7 -- research_agent/
```

## Risks to Scrutinize

These are the Feed-Forward risks flagged during planning and implementation:

1. **Tone injection security** — `<tone_instruction>` must be OUTSIDE `<instructions>` block. System prompts must declare "style only" role. Free-text capped at 500 chars. Verify the exact string assembly in `synthesize_report()` and `synthesize_final()`.

2. **gap_schema crash prevention** — `_update_gap_states()` line 169 calls `self.schema_path.parent`. The fallback must set `self.schema_path` (not just load the schema) or it crashes with `AttributeError`. Verify the fallback at agent.py line ~478.

3. **`_parse_template` private import** — `cli.py` imports the private `_parse_template()` function for `--list-contexts`. Is this acceptable or should there be a thin public wrapper?

4. **Per-field try/except isolation** — A malformed `blocked_domains` field should NOT prevent `synthesis_tone` from parsing. Verify field independence in `context.py`.

5. **Domain matching** — Must use dot-boundary check (`host == domain or host.endswith(f".{domain}")`), never bare `endswith()`. Verify in `search.py`.

## Review Checklist (from CODEX-REVIEW-GATE.md)

- [ ] Public result shapes consistent across CLI, Python API, MCP, saved reports
- [ ] New paths preserve SSRF protection, sanitization, prompt-injection defenses
- [ ] Context/gap/state changes preserve additive behavior and rollback safety
- [ ] Test gaps stated explicitly
- [ ] Run `python3 -m pytest tests/ -v` (920 tests must pass)

## Known Test Gap

The plan specifies ~38 new tests that have NOT been written yet. Review should flag specific test gaps but not block on them — tests are a separate session.

## Bring Findings Back

After review, write findings to `docs/reviews/2026-03-06-cycle-24-codex-findings.md` with:
- Priority (P1/P2/P3) per CODEX-REVIEW-GATE priority order
- File + line number for each finding
- Whether the finding is a blocker or advisory
- A recommended fix order if multiple P1s exist

Then Claude Code will run `/workflows:review` as the compound review pass.
