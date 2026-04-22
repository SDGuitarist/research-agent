# HANDOFF — Research Agent

**Date:** 2026-04-21
**Branch:** `main`
**Phase:** Work COMPLETE + Review fixes applied. Ready for Compound.

## Current State

All 4 Cycle 29 work sessions shipped + Codex review fixes applied. Three features: skeptic enforcement, snippet/summary quality gate with noun-phrase fallback, evidence-tier labeling with mid-report reminder.

**Key commits:**
- `cf1052b` — feat(29-1): extract and enforce skeptic critical findings
- `1d26e21` — feat(29-2): snippet/summary quality gate with noun-phrase fallback
- `f97918b` — feat(29-3): evidence-tier labeling with mid-report reminder
- `45943e3` — test(29-4): integration tests for enforcement and evidence tiers
- (pending) — fix(29-review): three-way contract, real-format regression tests

**Tests:** 1070 passing

## Review Fixes Applied

1. **Three-way contract** — Strengthened `<critical_findings>` enforcement from "refute or incorporate" to three specific options: (a) remove claim, (b) mark [Disputed] with reason, (c) cite additional evidence. Tests updated.
2. **Real-format regression tests** — Added 3 tests using actual skeptic output shapes: combined-mode `[Evidence][Critical Finding]` with indented bullets, deep-mode multiline format, and non-critical lens tag filtering.
3. **Feed-forward validation gap** — See below.

## Deferred: Session 4 Live Validation

**Status:** DEFERRED — API key is a placeholder (`your-anthr...`), no live queries possible.
**What was planned:** Run one deep-mode query, inspect final 3 sections for evidence-tier labels. If absent in >50%, add per-section reminder.
**Unblock condition:** Replace `.env` `ANTHROPIC_API_KEY` with a valid key, then run: `python3 main.py --deep "impact of AI on healthcare workforce"` and check the last 3 `##` sections for `[Documented]`/`[Inferred]`/`[Illustrative]`/`[Speculative]` labels.
**Impact if skipped:** Mid-report reminder may be insufficient for deep-mode reports (~3500 words). C33 adds post-synthesis extraction and validation as a fallback.

## Three Questions

1. **Hardest judgment call in this review?** Whether the three-way contract wording is specific enough. "Refute or incorporate" was vague — the model could claim to "incorporate" without actually changing anything. The three options (remove, mark [Disputed], cite evidence) are concrete actions the model can take.
2. **What did you consider flagging but chose not to, and why?** The regex handling `[Evidence][Critical Finding]` — it works because the regex matches `[critical finding]` as a substring within the longer bracket sequence. This is coincidental correctness, not intentional design. Chose not to flag because: (a) the regression tests now prove it works, and (b) making the regex explicitly handle lens prefixes would add complexity for no behavioral change.
3. **What might this review have missed?** Token budget impact. Evidence-tier instructions add ~200 tokens to every synthesis prompt. Neither `synthesize_report()` nor `synthesize_final()` registers the tier instruction with `allocate_budget()`. At current prompt sizes this is fine, but deep-mode reports with long contexts could hit the budget ceiling. Worth checking in C30 if budget violations appear.

## Deferred Items

- **ANTHROPIC_ERRORS consumption at 10+ call sites** — mechanical replacement for micro-cycle
- **MCP `--cost` + `--critique-history` tools** (#123) — Cycle 31
- **A/B live validation** — run `scripts/validate_cutoff_ab.py` when API keys renewed
- **Session 4 live tier-label validation** — run deep-mode query when API key replaced (see above)

## Next Phase

**Compound** — Document Cycle 29 patterns in `docs/solutions/`.

### Prompt for Next Session

```
Read HANDOFF.md. Run /workflows:compound for Cycle 29.
Key patterns to document: three-way enforcement contract, quality gate heuristic,
evidence-tier vocabulary module, regex coincidental correctness.
Start with /compound-start to load lessons and kick off.
```
