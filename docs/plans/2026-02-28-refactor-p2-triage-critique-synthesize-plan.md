---
title: "refactor: P2 Triage — Critique & Synthesize Cleanup"
type: refactor
status: active
date: 2026-02-28
origin: docs/brainstorms/2026-02-28-p2-triage-critique-synthesize-brainstorm.md
feed_forward:
  risk: "Whether removing query_domain from save_critique changes filename format enough to affect load_critique_history's file discovery"
  verify_first: true
---

# refactor: P2 Triage — Critique & Synthesize Cleanup

## Enhancement Summary

**Deepened on:** 2026-02-28
**Agents used:** kieran-python-reviewer, code-simplicity-reviewer, pattern-recognition-specialist
**Sections enhanced:** Decisions, Technical Considerations, Implementation Plan (Sessions 1 & 2)

### Key Improvements from Deepening

1. **Drop `to_dict()`** — one call site; `dataclasses.asdict()` + 2 lines for computed properties is simpler and matches the `_gap_to_dict()` pattern in `state.py`
2. **Rename `defaults()` → `fallback()`** — matches `ContextResult` state-name convention (`loaded`, `failed`, etc.)
3. **Rename `_build_generic_final_sections` → `_build_default_final_sections`** — matches `_default_critique` naming; no `_generic_` prefix precedent in codebase
4. **Add missing-key validation to `from_parsed`** — explicit `ValueError` instead of unhelpful `KeyError`
5. **Tighten `parsed: dict` → `dict[str, int]`** — self-documenting type hint
6. **Found 2 missed test assertions** — `test_yaml_roundtrip` and `test_empty_domain_uses_unknown` assert on slug-based filenames that change
7. **Inline `start_section=5`** — no callers vary it; use a constant, not a parameter

## Prior Phase Risk

> **Least confident:** Whether removing `query_domain` from `save_critique` changes the filename format enough to affect `load_critique_history`'s file discovery. Need to verify the glob pattern doesn't depend on the slug.

**Resolution:** Verified safe. `load_critique_history` uses `critique-*.yaml` glob (`context.py:441`). The `*` matches any slug+timestamp combination. New filename `critique_{timestamp}.yaml` matches the same glob. No migration needed.

## Overview

Three accumulated P2 review findings in the critique/synthesize subsystem, all subtractive refactoring:

1. **Remove `query_domain` YAGNI** — Delete a field, 2 prompt lines, slug logic, and construction args that serve no consumer. (~20 lines deleted)
2. **Centralize dimension construction** — Add `from_parsed()` and `fallback()` classmethods to `CritiqueResult`, replacing 3 duplicated construction sites. Serialization stays inline in `save_critique` using `dataclasses.asdict()`. (~10 lines added, ~25 deleted)
3. **Extract default section_list helper** — Replace inline string duplication in `synthesize_final` with a `_build_default_final_sections` helper. (~10 lines added, ~15 deleted)

Net change: ~-30 lines.

## Decisions

### Decision 1: Filename becomes `critique-{timestamp}.yaml`

Drop the slug, keep the hyphen separator. The timestamp is unique, and `load_critique_history` globs on `critique-*.yaml` — the hyphen after `critique` is literal in the glob, so the separator MUST remain a hyphen. New format: `critique-1234567890.yaml`. All existing files on disk already have `slug = "unknown"` so the slug never carried information.

(see brainstorm: Decision 1 — remove `query_domain` entirely)

### Decision 2: `from_parsed` never sanitizes — caller sanitizes before calling

`evaluate_report` passes raw parsed values. `critique_report_file` sanitizes the parsed dict before calling `from_parsed`. This matches the "sanitize at boundary" convention from `docs/solutions/security/non-idempotent-sanitization-double-encode.md`.

(see brainstorm: Decision 2 — centralize with factory methods)

### Decision 3: Separate `_build_default_final_sections` helper

A small focused function (~8 lines) that accepts `has_skeptic: bool`. Section numbering starts at 5 (hardcoded constant, not a parameter — no callers vary it). Name follows `_default_critique` precedent; no `_generic_` prefix in codebase.

(see brainstorm: Decision 3 — unify section_list through existing helper)

### Decision 4: Switch test construction to keyword arguments

All 12 test sites using positional `CritiqueResult(3, 4, 3, 3, 4, "", "")` will break when `query_domain` is removed (positional shift). Convert them to keyword construction to prevent this class of breakage for future field changes. This matches the `ContextResult` pattern where tests use factory classmethods.

## Technical Considerations

- **Existing YAML files on disk** still have `query_domain` key. `_validate_critique_yaml` silently ignores unknown keys (dict `.get()` semantics). No migration needed — the key is just unused.
- **`_parse_critique_response`** currently returns `query_domain` in its dict from the regex loop. After removing the field from the `for field in (...)` list, the parser no longer extracts it. Claude still emits the line (until prompt text is also updated), but it's ignored.
- **`_default_critique(query: str)`** takes a `query` argument it never uses. Replace with `CritiqueResult.fallback()` classmethod with no arguments. Two call sites drop the unused arg.
- **Serialization in `save_critique`** — use `dataclasses.asdict(result)` + add `overall_pass`, `mean_score`, `timestamp` manually (3 lines). No `to_dict()` method needed — only one call site, and this matches the `_gap_to_dict()` pattern in `state.py` where serialization lives at the consumption site.
- **`DIMENSIONS` tuple** (`critique.py:27`) is already canonical. `from_parsed` uses it via `{d: parsed[d] for d in DIMENSIONS}`. No new hard-coded dimension lists.
- **`from_parsed` validates missing keys** — raises `ValueError` with a clear message listing missing dimensions, instead of an unhelpful `KeyError`. Note: `_parse_critique_response` always populates all keys (defaults to 3), so this is defensive, not reachable under normal flow.
- **Default section numbering** starts at 5 (assumes 4 draft sections). This is a pre-existing simplification, not introduced by this refactor. Hardcoded as a constant inside the helper, not a function parameter — no callers vary it.

## System-Wide Impact

- **Interaction graph:** `CritiqueResult` is constructed in `critique.py` and consumed in `agent.py` (passes to `context.py`'s `_summarize_patterns` via `load_critique_history`). No callbacks or observers. `synthesize_final` is called only from `agent.py`.
- **Error propagation:** `from_parsed` raises `ValueError` with descriptive message on missing dimension keys (improvement over bare `KeyError`). `fallback()` always succeeds.
- **State lifecycle risks:** None. All changes are to data shapes and construction patterns, not state management.
- **API surface parity:** `CritiqueResult` is not part of the public API (`__init__.py` does not export it). No external callers affected.

## Implementation Plan

### Session 1: Remove `query_domain` + Centralize Dimensions (~80 lines)

**Files:** `critique.py`, `context.py`, `tests/test_critique.py`, `tests/test_results.py`, `tests/test_public_api.py`, `tests/test_synthesize.py`, `tests/test_context.py`

**Step 1: Remove `query_domain` from `CritiqueResult` and all production code**

1. `critique.py:57` — delete `query_domain: str` field
2. `critique.py:48-56` — remove from docstring
3. `critique.py:101` — remove `"query_domain"` from `_parse_critique_response` field loop
4. `critique.py:183` — delete `QUERY_DOMAIN:` line from `evaluate_report` prompt
5. `critique.py:208` — delete `query_domain = parsed.get(...)` extraction
6. `critique.py:218` — delete `query_domain=query_domain` kwarg
7. `critique.py:270` — delete `QUERY_DOMAIN:` line from `critique_report_file` prompt
8. `critique.py:287` — delete `query_domain = sanitize_content(...)` extraction
9. `critique.py:297` — delete `query_domain=query_domain` kwarg
10. `critique.py:311` — delete `query_domain=""` from `_default_critique`
11. `critique.py:327-328` — replace slug logic with `filename = f"critique-{timestamp}.yaml"`
12. `critique.py:340` — delete `"query_domain": result.query_domain` from YAML dict
13. `context.py:346` — remove `"query_domain"` from `_validate_critique_yaml` field loop

**Step 2: Add factory classmethods to `CritiqueResult`**

Add two classmethods after the field declarations:

```python
@classmethod
def from_parsed(cls, parsed: dict[str, int], weaknesses: str, suggestions: str) -> "CritiqueResult":
    """Construct from LLM-parsed scores dict.

    Text fields are passed separately because sanitization
    requirements differ between call sites.

    Raises:
        ValueError: If any dimension key is missing from parsed.
    """
    missing = [d for d in DIMENSIONS if d not in parsed]
    if missing:
        raise ValueError(f"from_parsed: missing dimension keys: {missing}")
    scores = {d: parsed[d] for d in DIMENSIONS}
    return cls(**scores, weaknesses=weaknesses, suggestions=suggestions)

@classmethod
def fallback(cls) -> "CritiqueResult":
    """Neutral fallback when critique API call fails."""
    scores = {d: 3 for d in DIMENSIONS}
    return cls(**scores, weaknesses="Critique unavailable (API error)", suggestions="")
```

**Step 3: Replace construction sites with classmethods**

1. `critique.py` `evaluate_report` (~line 210) — replace 10-line construction with `CritiqueResult.from_parsed(parsed, weaknesses=weaknesses, suggestions=suggestions)`
2. `critique.py` `critique_report_file` (~line 289) — caller sanitizes `weaknesses`/`suggestions` before calling `from_parsed`
3. `critique.py` `_default_critique` — replace body with `return CritiqueResult.fallback()`, then inline at call sites and delete the function
4. `critique.py` `save_critique` (~line 332) — replace manual dict build with `dataclasses.asdict(result)` + add computed properties:
   ```python
   data = dataclasses.asdict(result)
   data["overall_pass"] = result.overall_pass
   data["mean_score"] = round(result.mean_score, 2)
   data["timestamp"] = timestamp
   ```

**Step 4: Update all tests**

- Convert 12 positional `CritiqueResult(...)` calls to keyword construction across `test_critique.py`, `test_results.py`, `test_public_api.py`
- Remove `query_domain` kwarg from all test constructions
- Update `test_synthesize.py:68` assertion that checks `result["query_domain"]` — remove it
- Update `test_critique.py` `test_yaml_roundtrip` (~line 165) — assertion `path.name.startswith("critique-music_")` must change to `path.name.startswith("critique-")`
- Update `test_critique.py` `test_empty_domain_uses_unknown` (~line 180) — assertion `"unknown" in path.name` must be removed or changed
- Update `test_context.py:785` validation test data — remove `query_domain` key (or leave it as ignored extra key)
- Add unit tests for `from_parsed` and `fallback` classmethods (including `from_parsed` with missing key → `ValueError`)

**Acceptance criteria:**
- [ ] `grep -rn "query_domain" research_agent/ --include="*.py"` returns zero results
- [ ] `DIMENSIONS` tuple is the only place dimension names are listed (except `CritiqueResult` field declarations and prompt text)
- [ ] No positional `CritiqueResult(...)` construction in tests
- [ ] All tests pass

### Session 2: Extract Generic Section List Helper (~30 lines)

**Files:** `synthesize.py`, `tests/test_synthesize.py`

**Step 1: Add `_build_default_final_sections` helper**

```python
_DEFAULT_FINAL_START = 5  # Assumes 4 generic draft sections

def _build_default_final_sections(has_skeptic: bool) -> str:
    """Build final section list for reports without a template."""
    parts = []
    n = _DEFAULT_FINAL_START
    if has_skeptic:
        parts.append(f"{n}. **Adversarial Analysis** — Synthesize the skeptic review findings.")
        n += 1
    parts.append(f"{n}. **Limitations & Gaps** — What sources don't cover, confidence levels.")
    parts.append("## Sources — All referenced URLs with [Source N] notation.")
    return "\n".join(parts)
```

**Step 2: Replace inline blocks in `synthesize_final`**

Replace lines 552-563 (the `else` branch) with:
```python
else:
    section_list = _build_default_final_sections(
        has_skeptic=bool(skeptic_findings),
    )
```

**Step 3: Update tests**

- Add test for `_build_default_final_sections` with skeptic and without
- Add positive assertion in `test_synthesize.py` that `"5. **Adversarial Analysis**"` appears in generic skeptic path
- Verify existing `test_skips_section_11_when_no_findings` still passes

**Acceptance criteria:**
- [ ] No inline section_list strings in `synthesize_final`
- [ ] `_build_default_final_sections` tested directly
- [ ] All tests pass

## Acceptance Criteria (Overall)

- [ ] `query_domain` fully removed from production code
- [ ] `CritiqueResult` construction uses `from_parsed()` and `fallback()` classmethods (3 sites)
- [ ] `DIMENSIONS` is the single source of truth for score field names
- [ ] No inline section_list strings in `synthesize_final`
- [ ] `save_critique` uses `dataclasses.asdict()` for serialization
- [ ] All 757+ tests pass
- [ ] Net line count decreases

## Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| Positional `CritiqueResult(...)` in tests breaks on field removal | Convert all 12 sites to keyword construction in same commit |
| Existing YAML files have `query_domain` key | `_validate_critique_yaml` ignores unknown keys; no migration needed |
| New filename `critique-{timestamp}.yaml` vs old `critique-{slug}_{timestamp}.yaml` | Glob `critique-*.yaml` matches both — hyphen separator preserved |
| `from_parsed` hides sanitization intent | Docstring documents "caller must sanitize if needed"; matches codebase convention |

## Sources & References

- **Origin brainstorm:** [docs/brainstorms/2026-02-28-p2-triage-critique-synthesize-brainstorm.md](docs/brainstorms/2026-02-28-p2-triage-critique-synthesize-brainstorm.md) — Key decisions: remove query_domain entirely, factory classmethods, separate generic helper
- **Review findings:** [docs/reviews/self-enhancing-agent/REVIEW-SUMMARY.md](docs/reviews/self-enhancing-agent/REVIEW-SUMMARY.md) P2 #21 (query_domain YAGNI), P2 #23 (duplicated dimensions); [docs/reviews/background-research-agents/REVIEW-SUMMARY.md](docs/reviews/background-research-agents/REVIEW-SUMMARY.md) P2 #17 (four-way branching)
- **Institutional learnings:**
  - [docs/solutions/security/non-idempotent-sanitization-double-encode.md](docs/solutions/security/non-idempotent-sanitization-double-encode.md) — sanitize-at-boundary convention
  - [docs/solutions/architecture/self-enhancing-agent-review-patterns.md](docs/solutions/architecture/self-enhancing-agent-review-patterns.md) — YAGNI removal precedent (domain parameter), CritiqueResult frozen dataclass confirmed
  - [docs/solutions/performance-issues/redundant-retry-evaluation-and-code-deduplication.md](docs/solutions/performance-issues/redundant-retry-evaluation-and-code-deduplication.md) — extraction pattern for shared utilities
- **Codebase patterns:** `ContextResult` classmethods (`context_result.py:56-96`), `ResearchMode` classmethods (`modes.py:81-164`) — established factory method convention for frozen dataclasses
- **SpecFlow analysis:** 14 gaps identified, 11 critical questions resolved. Key gaps addressed: filename slug replacement (Gap 1), sanitization policy (Gap 6), `to_dict` shape (Gap 7), test positional breakage (Gap 3)

## Feed-Forward

- **Hardest decision:** Whether `from_parsed` should handle sanitization or leave it to the caller. Chose caller-sanitizes because it matches the established boundary convention and avoids a boolean parameter. But this means `critique_report_file` has a sanitization step that `evaluate_report` doesn't — the asymmetry is intentional but could confuse a future reader.
- **Rejected alternatives:** (1) Making `DIMENSIONS` drive the dataclass fields via metaclass — too clever for 5 fields. (2) Extending `_build_final_sections` with `template=None` — adds complexity to a clean function. (3) Keeping `query_domain` as deprecated — pointless for a personal CLI tool. (4) Adding `to_dict()` on `CritiqueResult` — only one call site; `dataclasses.asdict()` + 2 lines is simpler and matches `state.py` pattern. (5) `start_section` as a function parameter — no callers vary it; constant is simpler.
- **Least confident:** Whether `dataclasses.asdict()` includes or excludes the `@property` computed fields (`overall_pass`, `mean_score`). It excludes them — only dataclass fields are included — so the manual additions in `save_critique` are required. Verify this during implementation.
