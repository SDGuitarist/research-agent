# P2 Triage: Critique & Synthesize Cleanup — Brainstorm

**Date:** 2026-02-28
**Cycle:** 23 (triage)
**Status:** Brainstorm complete — ready for planning

---

## What We're Building

A single triage cycle to resolve 3 accumulated P2 review findings, all in the critique/synthesize area:

1. **Four-way section_list branching** (`synthesize.py:546-564`) — The non-template path duplicates "Limitations & Gaps" and "Sources" strings instead of using the existing `_build_final_sections` helper. Two inline string blocks that should be one function call.

2. **`query_domain` YAGNI** (`critique.py` throughout) — A `query_domain` field on `CritiqueResult` is extracted from LLM output, stored in YAML, validated on read, and used for filename slugs — but never read back for filtering. ~20 lines of machinery for a feature that doesn't exist.

3. **Duplicated dimension constants** (`critique.py`, 8 locations) — The 5 critique dimensions (`source_diversity`, `claim_support`, `coverage`, `geographic_balance`, `actionability`) are listed by hand in 8 places (42 lines). The canonical `DIMENSIONS` tuple exists but only 3 call sites use it. Adding a 6th dimension requires editing 8+ locations.

## Why These Together

All three are in the critique/synthesize subsystem. Findings #2 and #3 both touch `critique.py` heavily. Fixing them together avoids re-reading and re-testing the same files across separate cycles.

## Key Decisions

### Decision 1: Remove `query_domain` entirely (not refactor)

The review said "remove, add later if needed." The field is pure YAGNI — no consumer reads it back. Removing it means:
- Delete from `CritiqueResult` dataclass
- Delete from both prompt templates
- Delete from `_parse_critique_response` field list
- Delete from both construction sites
- Delete slug logic from `save_critique` (use a simpler filename)
- Delete from `_validate_critique_yaml` field list
- Existing YAML files on disk still have the field — `yaml.safe_load` will just ignore it

### Decision 2: Centralize dimension construction with factory methods

The `CritiqueResult` dataclass fields can't be generated from `DIMENSIONS` (frozen dataclass needs explicit typed fields). But construction, defaults, and serialization can be:
- `CritiqueResult.from_parsed(parsed: dict)` — replaces 2 identical 5-line construction blocks
- `CritiqueResult.defaults()` — replaces the 5-line default block
- `result.to_scores_dict()` — replaces the 5-line serialization in `save_critique`
- Test file imports `DIMENSIONS` instead of re-declaring

The prompt text duplication (2 locations with slightly drifted wording) is harder — prompts aren't code. Keep them as-is but verify wording matches.

### Decision 3: Unify `synthesize_final` section_list through the existing helper

`_build_final_sections` already handles template + skeptic branching cleanly. The fix is to make the non-template path use the same function by passing `template=None`:
- Extend `_build_final_sections` to accept `template=None` and generate generic sections
- Collapse the 19-line branch in `synthesize_final` to a single function call

## Open Questions

None — all three fixes have clear solutions from the original reviews.

## Feed-Forward

- **Hardest decision:** Whether to centralize the prompt text duplication (Finding #3). Decided not to — prompt strings aren't code, and a shared constant for LLM rubric text would be awkward. The wording drift is low-risk.
- **Rejected alternatives:** (1) Making `DIMENSIONS` drive the dataclass fields via `__init_subclass__` or metaclass — too clever for 5 fields. (2) Keeping `query_domain` but deprecating it — pointless for a personal CLI tool.
- **Least confident:** Whether removing `query_domain` from `save_critique` changes the filename format enough to affect `load_critique_history`'s file discovery. Need to verify the glob pattern doesn't depend on the slug.
