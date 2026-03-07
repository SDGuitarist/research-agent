---
title: "feat: Swappable Context Profiles"
type: feat
status: active
date: 2026-03-06
origin: docs/brainstorms/2026-03-06-swappable-context-profiles-brainstorm.md
feed_forward:
  risk: "How preferred_domains scoring boost integrates with evaluate_sources() — the boost needs to happen post-LLM-scoring without distorting the gate decisions"
  verify_first: true
---

# feat: Swappable Context Profiles (Cycle 24)

## Prior Phase Risk

> "Least confident: How `preferred_domains` scoring boost integrates with `evaluate_sources()` — this function currently sends content to Haiku for scoring. The boost needs to happen post-LLM-scoring without distorting the gate decisions."

This plan addresses it by applying the boost post-aggregation in `evaluate_sources()` (after `_aggregate_by_source()`), keeping `SourceScore.score` as `int` internally and applying the float boost only at the gate comparison. See Session 3 for details.

## Overview

Enrich the existing `contexts/` system with four new YAML frontmatter fields and a `--list-contexts` CLI flag. The infrastructure (context files, `--context` flag, auto-detection, `ContextResult`/`ReportTemplate`) already exists. This cycle adds structured fields that affect pipeline behavior beyond prompt content.

(See brainstorm: `docs/brainstorms/2026-03-06-swappable-context-profiles-brainstorm.md`)

## Key Decisions (carried from brainstorm)

1. **Keep `--context`** — no rename to `--profile` (avoids CLI + MCP breakage)
2. **Blocked domains: hard filter** — skip before fetch, all search entry points
3. **Preferred domains: soft boost** — +0.5 post-aggregation in relevance scoring
4. **Gap schema: path reference only** — warn if missing, CLI `--schema` takes precedence
5. **Synthesis tone: presets + custom** — `executive`/`technical`/`casual` presets, or free-text
6. **`--list-contexts` CLI flag** — show name, description, configured fields

## Architectural Decision: Data Model

New fields go on a **new `ContextProfile` frozen dataclass**, NOT on `ReportTemplate`.

**Rationale:** `ReportTemplate` holds report structure concerns (section headings, context_usage). Source preferences and gap schema paths are operational pipeline parameters — different concern. Mixing them violates single-responsibility and breaks every existing `ReportTemplate` test.

```python
# context_result.py
@dataclass(frozen=True)
class ContextProfile:
    preferred_domains: tuple[str, ...]  = ()
    blocked_domains: tuple[str, ...]    = ()
    gap_schema: str                     = ""
    synthesis_tone: str                 = ""
```

Carried on `ContextResult` as `profile: ContextProfile | None = None`, alongside the existing `template` field. Passed through `ContextResult.loaded()` factory.

## Resolved SpecFlow Gaps

These gaps were identified by flow analysis and resolved here:

| Gap | Resolution |
|-----|-----------|
| **Where do new fields live?** (Q1) | New `ContextProfile` dataclass on `ContextResult`, separate from `ReportTemplate` |
| **Tone prompt injection** (Q2) | `sanitize_content()` + wrap in `<tone_instruction>` XML tag with "style only" guard. Context files are trusted-author input, same trust level as template sections |
| **--schema vs gap_schema precedence** (Q3) | CLI `--schema` wins. Log warning if both are set. If no `--schema`, use profile's `gap_schema` |
| **blocked_domains scope** (Q4) | All entry points. Single `filter_blocked_urls()` helper in `search.py`, called after every search |
| **Domain matching** (Q5) | Suffix matching with dot-boundary: `example.com` blocks `sub.example.com` but NOT `notexample.com` |
| **Boost application point** (Q6) | Post-aggregation. Keep `SourceScore.score` as `int`. Apply boost as float only at gate comparison |
| **Which synthesis functions get tone** (Q7) | `synthesize_report()` and `synthesize_final()` only. Skip `synthesize_draft()` (objective) and `synthesize_mini_report()` (internal) |
| **Preset definitions** (Q8) | Constants dict in `synthesize.py` (co-located with consumers) |
| **gap_schema path validation** (Q9) | Reject absolute paths and `..` components. Resolve relative to project root |
| **blocked + preferred overlap** (Q12) | Log warning during parsing, don't error |
| **Unrecognized preset name** (Q13) | Treat as free-text, log warning listing valid presets |
| **Prefetched content filtering** (Q5 from SpecFlow) | `filter_blocked_urls()` applied to search results before `_split_prefetched()`, so prefetched blocked content is also filtered |

## System-Wide Impact

- **Interaction graph:** YAML parsing → `ContextProfile` → carried on `ContextResult` → read by `agent.py` → passed to `search.py` (blocked), `relevance.py` (preferred), `synthesize.py` (tone), `agent.py` (gap_schema fallback)
- **Error propagation:** Malformed YAML fields → caught in `_parse_template()` → `ContextResult.failed()` → research aborts with clear error. Missing gap_schema file → `logger.warning()` → research continues without gaps
- **State lifecycle risks:** None — all new fields are read-only configuration. No persistent state changes
- **API surface parity:** MCP `list_contexts` tool already exists. No new MCP tools needed, but MCP instructions string needs updating if behavior changes. New fields are transparent — they affect pipeline behavior, not MCP interface

## Acceptance Criteria

- [ ] `ContextProfile` frozen dataclass in `context_result.py` with 4 fields
- [ ] `_parse_template()` extracts new fields from YAML frontmatter
- [ ] Fields sanitized at parse boundary (once, never double-sanitized)
- [ ] `filter_blocked_urls(results, blocked_domains)` helper in `search.py`
- [ ] Blocked domain filter applied at ALL search entry points (pass1, pass2, sub-queries, iteration, coverage retry)
- [ ] Subdomain matching: `example.com` blocks `sub.example.com` but not `notexample.com`
- [ ] Preferred domain boost (+0.5) applied post-aggregation in `evaluate_sources()`
- [ ] `SourceScore.score` stays `int`; boost applied only at gate comparison
- [ ] `gap_schema` path validated (no `..`, no absolute), resolved relative to project root
- [ ] CLI `--schema` takes precedence over profile `gap_schema`; warning logged if both set
- [ ] Tone presets (`executive`, `technical`, `casual`) defined as constants
- [ ] Tone injected into `synthesize_report()` and `synthesize_final()` only
- [ ] Free-text tone sanitized + wrapped in `<tone_instruction>` XML tag
- [ ] `--list-contexts` CLI flag shows name + configured field summary
- [ ] `pfe.md` updated with example profile fields
- [ ] Tests for: parsing (valid, missing, malformed), domain filtering, domain matching, boost application, tone injection, gap_schema resolution, --list-contexts output
- [ ] All existing tests pass (920+)

## Implementation Phases

### Session 1: Data Model + Parsing (~80 lines)

**Files:** `context_result.py`, `context.py`

**Tasks:**
1. Add `ContextProfile` frozen dataclass to `context_result.py`
2. Add `profile: ContextProfile | None = None` field to `ContextResult`
3. Update `ContextResult.loaded()` factory to accept `profile` parameter
4. Extend `_parse_template()` in `context.py` to extract new YAML fields:
   - `preferred_domains` → `tuple[str, ...]` (sanitize each, convert list to tuple)
   - `blocked_domains` → `tuple[str, ...]` (same)
   - `gap_schema` → `str` (validate: no `..`, no absolute path)
   - `synthesis_tone` → `str` (sanitize)
5. Validate `blocked_domains` ∩ `preferred_domains` overlap → `logger.warning()`
6. Construct `ContextProfile` and pass to `ContextResult.loaded()`
7. Update `pfe.md` with example fields

**Tests (~15):**
- Parse valid profile with all fields
- Parse profile with no new fields (backwards compatibility)
- Parse profile with partial fields (only blocked_domains)
- Malformed fields (blocked_domains as string instead of list)
- gap_schema path validation (reject `../`, absolute paths)
- Overlap warning between blocked and preferred
- Sanitization applied to domain strings and tone

**Commit:** `feat(24-1): add ContextProfile dataclass and YAML parsing`

### Session 2: Blocked Domains Filter (~60 lines)

**Files:** `search.py`, `agent.py`

**Tasks:**
1. Add `filter_blocked_urls(results, blocked_domains)` to `search.py`:
   - Extract domain from each result URL via `urlparse`
   - Suffix match with dot-boundary check: `url_domain == blocked or url_domain.endswith("." + blocked)`
   - Return filtered list
   - Log count of filtered results
2. Thread `blocked_domains` from `self._run_context.profile` through `agent.py`
3. Apply filter after EVERY search call site:
   - `_research_with_refinement()` pass 1 and pass 2
   - `_research_deep()` pass 1 and pass 2
   - `_search_sub_queries()` (covers decomposition AND iteration)
   - `_try_coverage_retry()`
4. Apply filter BEFORE `_split_prefetched()` so prefetched blocked content is also removed
5. Log warning if filtering reduces count below `mode.min_sources_full_report`

**Tests (~12):**
- `filter_blocked_urls` with exact domain match
- Subdomain matching (sub.example.com blocked by example.com)
- Non-matching similar domain (notexample.com NOT blocked by example.com)
- Empty blocked_domains (no-op)
- No context loaded (no-op)
- Integration: blocked URL removed from search results in agent flow

**Commit:** `feat(24-2): add blocked_domains hard filter across all search paths`

### Session 3: Preferred Domains Boost (~40 lines)

**Files:** `relevance.py`, `agent.py`

**Tasks:**
1. Add `preferred_domains: tuple[str, ...] = ()` parameter to `evaluate_sources()`
2. After `_aggregate_by_source()` returns `source_scores` (line 305), apply boost:
   ```python
   # Post-aggregation boost for preferred domains
   for source in source_scores:
       domain = _extract_domain(source["url"])
       if _is_preferred(domain, preferred_domains):
           source["_boosted_score"] = source["score"] + 0.5
       else:
           source["_boosted_score"] = source["score"]
   ```
3. Use `source["_boosted_score"]` for the gate comparison (line 316) instead of `source["score"]`
4. Log the boost: `"Source %d (%s): score %d/5 (+0.5 preferred) — %s"`
5. `_is_preferred()` uses same suffix matching as blocked domains
6. Thread `preferred_domains` from `self._run_context.profile` through `agent.py` into `evaluate_sources()`

**Key design:** `SourceScore.score` stays `int`. The `_boosted_score` is a transient float used only for the KEEP/DROP decision. Logging shows the original int score with a "(+0.5 preferred)" annotation. This avoids rippling type changes through the codebase.

**Tests (~10):**
- Boost applied to preferred domain source
- Boost causes a source at cutoff-1 to survive (e.g., score 2 + 0.5 with cutoff 3 → still drops; score 3 + 0.5 → keeps)
- No boost for non-preferred domains
- Subdomain matching for preferred
- Empty preferred_domains (no-op)
- Boost does not change stored score (only gate comparison)

**Commit:** `feat(24-3): add preferred_domains relevance boost`

### Session 4: Synthesis Tone (~50 lines)

**Files:** `synthesize.py`, `agent.py`

**Tasks:**
1. Define tone presets as a module-level dict in `synthesize.py`:
   ```python
   TONE_PRESETS: dict[str, str] = {
       "executive": (
           "Write for a non-technical executive audience. Use confident, direct language. "
           "Lead with implications and recommendations. Minimize jargon."
       ),
       "technical": (
           "Write for a technical audience familiar with the domain. "
           "Include specific data points, methodologies, and technical details. "
           "Use precise terminology."
       ),
       "casual": (
           "Write in a conversational, accessible tone. "
           "Use plain language and concrete examples. "
           "Avoid formal structure where natural flow works better."
       ),
   }
   ```
2. Add `_build_tone_instruction(tone: str) -> str` helper:
   - If `tone` matches a preset key (case-insensitive), expand it
   - If not, treat as free-text (log warning listing valid presets)
   - Wrap in `<tone_instruction>` XML tag
   - Return empty string if tone is empty
3. Add `synthesis_tone: str = ""` parameter to `synthesize_report()` and `synthesize_final()`
4. Inject `tone_instruction` into the `<instructions>` block (alongside `context_instruction`, `mode_instructions`)
5. Thread `synthesis_tone` from `self._run_context.profile` through `agent.py`
6. Do NOT inject into `synthesize_draft()` (preserves objective factual analysis) or `synthesize_mini_report()` (internal)

**Tests (~8):**
- Preset expansion (executive → full text)
- Case-insensitive preset matching
- Free-text passthrough
- Unrecognized preset treated as free-text with warning
- Empty tone (no-op, no XML tag added)
- Tone appears in synthesize_report prompt
- Tone appears in synthesize_final prompt
- Tone does NOT appear in synthesize_draft prompt

**Commit:** `feat(24-4): add synthesis_tone presets and injection`

### Session 5: Gap Schema + CLI + Cleanup (~50 lines)

**Files:** `agent.py`, `cli.py`, `context.py`

**Tasks:**
1. **Gap schema fallback** in `agent.py`:
   - If `self.schema_path` is None and profile has `gap_schema`, resolve it relative to project root
   - Validate: reject `..` and absolute paths (reuse validation from Session 1)
   - If file doesn't exist, `logger.warning()` and proceed without gap awareness
   - If both `--schema` and profile `gap_schema` are set, `logger.warning()` and use `--schema`
2. **`--list-contexts` CLI flag** in `cli.py`:
   - Add `parser.add_argument("--list-contexts", action="store_true")`
   - Add early exit block (after `--list` check)
   - Implement `list_contexts_cli()`:
     - For each context file, call `_parse_template()` to get full profile data
     - Display: name, configured fields (e.g., "blocked: 2 domains, tone: executive, gap_schema: gaps/pfe.yaml")
     - Handle parse errors gracefully (show name + "parse error")
3. Update `list_available_contexts()` in `context.py` if needed for richer data

**Tests (~8):**
- gap_schema fallback when no --schema CLI arg
- --schema CLI takes precedence over gap_schema
- gap_schema missing file → warning, continues
- gap_schema path traversal rejection
- --list-contexts output format
- --list-contexts with no context files
- --list-contexts with parse error in one file

**Commit:** `feat(24-5): add gap_schema fallback and --list-contexts CLI`

## Alternative Approaches Considered

1. **Add fields to `ReportTemplate`** — Rejected: breaks every test that constructs `ReportTemplate`, mixes report-structure and pipeline-behavior concerns
2. **Store profile data directly on `ContextResult`** (flat fields) — Rejected: clutters an already 5-field dataclass. A separate `ContextProfile` is cleaner and more extensible
3. **Filter blocked domains in `fetch.py`** — Rejected: too late — we'd still waste search result slots on blocked URLs. Filtering in `search.py` (post-search, pre-fetch) is the right level
4. **Change `SourceScore.score` to `float`** — Rejected: ripples through logging, display, gate comparison. Transient `_boosted_score` avoids all type changes

## Dependencies & Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Missing a search entry point for blocked_domains | HIGH | SpecFlow identified 6 sites. Grep for all `search(` and `_search_sub_queries` calls. Test with a blocked domain in deep mode |
| preferred_domains boost distorting gate decisions | MEDIUM | +0.5 on a 1-5 scale is small. A score-2 source can't jump to KEEP (cutoff 3). Only score-3 sources get meaningfully boosted. Verify with edge case tests |
| Tone prompt injection | LOW | Context files are trusted-author input. `sanitize_content()` + XML tag boundary provides adequate defense. Same trust level as existing `context_usage` field |
| Breaking existing tests | MEDIUM | `ContextProfile` has all-default fields. `ReportTemplate` unchanged. `ContextResult.loaded()` gets a new optional kwarg. Existing callers unaffected |

## Success Metrics

- All 920+ existing tests pass
- ~53 new tests covering all new fields and integration points
- `pfe.md` demonstrates all 4 new fields
- `--list-contexts` shows clean output with field summary
- Pipeline behavior unchanged when no new fields are configured (backwards compatible)

## Sources & References

### Origin

- **Brainstorm document:** [docs/brainstorms/2026-03-06-swappable-context-profiles-brainstorm.md](docs/brainstorms/2026-03-06-swappable-context-profiles-brainstorm.md) — Key decisions carried forward: keep `--context` (no rename), hard filter for blocked domains, soft boost for preferred domains, presets + custom for tone

### Internal References

- `research_agent/context_result.py` — `ReportTemplate`, `ContextResult` dataclasses
- `research_agent/context.py:39-123` — `_parse_template()` YAML parser
- `research_agent/relevance.py:305-323` — source aggregation and gate comparison
- `research_agent/synthesize.py:263,612` — instruction block injection points
- `research_agent/cli.py:116,196` — `--list` flag pattern
- `docs/solutions/security/non-idempotent-sanitization-double-encode.md` — sanitize once, never twice
- `docs/solutions/logic-errors/defensive-yaml-frontmatter-parsing.md` — YAML parsing gotchas

### Institutional Learnings Applied

- Sanitize at boundary, never chain (`non-idempotent-sanitization-double-encode.md`)
- Check `isinstance(bool)` before `isinstance(int)` for YAML fields (`python-bool-is-int-yaml-validation.md`)
- Place new frozen dataclass fields near related concerns (`tiered-model-routing-planning-vs-synthesis.md`)
- Use four-state results, not None (`context-path-traversal-defense-and-sanitization.md`)

## Feed-Forward

- **Hardest decision:** Whether to put new fields on `ReportTemplate` or create a separate `ContextProfile`. Chose separation — `ReportTemplate` is about report structure, profile fields are about pipeline behavior. Different concerns, different dataclass.
- **Rejected alternatives:** Flat fields on `ContextResult` (clutters), `SourceScore.score` as float (type ripple), filtering in `fetch.py` (too late), blocking in relevance scoring (soft filter complexity).
- **Least confident:** Session 2's blocked_domains coverage across all 6+ search entry points. SpecFlow identified the sites, but the actual `agent.py` plumbing is complex with deep/standard/quick branching. The work session should grep for ALL search calls and verify each one gets the filter. If one is missed, blocked content leaks through in specific modes.
