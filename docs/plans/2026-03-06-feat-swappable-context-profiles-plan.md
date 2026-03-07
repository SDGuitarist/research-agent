---
title: "feat: Swappable Context Profiles"
type: feat
status: active
date: 2026-03-06
origin: docs/brainstorms/2026-03-06-swappable-context-profiles-brainstorm.md
feed_forward:
  risk: "preferred_domains must have a real behavioral effect under integer scores/cutoff — +0.5 on int scores with int cutoff is a no-op"
  verify_first: true
---

# feat: Swappable Context Profiles (Cycle 24)

## Prior Phase Risk

> "Least confident: How `preferred_domains` scoring boost integrates with `evaluate_sources()` — this function currently sends content to Haiku for scoring. The boost needs to happen post-LLM-scoring without distorting the gate decisions."

This plan addresses it by **deferring `preferred_domains` from this cycle**. Analysis showed the original +0.5 boost is a no-op: scores are `int` (1-5), `relevance_cutoff` is `int` (3 in all modes), so score 2 + 0.5 = 2.5 still drops, and score 3 already passes without any boost. A +1 boost would have real effect but was rejected as too aggressive — it would rescue genuinely low-quality sources just because they're from a preferred domain. The field is parsed and stored (for forward compatibility) but has no pipeline effect this cycle. See "Deferred: preferred_domains" section below.

## Overview

Enrich the existing `contexts/` system with four new YAML frontmatter fields and a `--list-contexts` CLI flag. The infrastructure (context files, `--context` flag, auto-detection, `ContextResult`/`ReportTemplate`) already exists. This cycle adds structured fields that affect pipeline behavior beyond prompt content.

(See brainstorm: `docs/brainstorms/2026-03-06-swappable-context-profiles-brainstorm.md`)

## Key Decisions (carried from brainstorm)

1. **Keep `--context`** — no rename to `--profile` (avoids CLI + MCP breakage)
2. **Blocked domains: hard filter** — skip before fetch, all search entry points
3. **Preferred domains: deferred** — parsed and stored but no pipeline effect this cycle (see rationale in Prior Phase Risk)
4. **Gap schema: path reference only** — warn if missing, profile-only (no CLI `--schema` flag this cycle)
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
| **gap_schema source** (Q3) | Profile-only this cycle. No CLI `--schema` flag exists; adding one is out of scope. `gap_schema` from profile is used as fallback when `self.schema_path` is None |
| **blocked_domains scope** (Q4) | All entry points. Single `filter_blocked_urls()` helper in `search.py`, called after every search |
| **Domain matching** (Q5) | Suffix matching with dot-boundary: `example.com` blocks `sub.example.com` but NOT `notexample.com` |
| **Boost application point** (Q6) | Deferred. +0.5 on int scores with int cutoff is a no-op. Field is parsed/stored for forward compatibility only |
| **Which synthesis functions get tone** (Q7) | `synthesize_report()` and `synthesize_final()` only. Skip `synthesize_draft()` (objective) and `synthesize_mini_report()` (internal) |
| **Preset definitions** (Q8) | Constants dict in `synthesize.py` (co-located with consumers) |
| **gap_schema path validation** (Q9) | Reject absolute paths and `..` components. Resolve relative to project root |
| **blocked + preferred overlap** (Q12) | Log warning during parsing, don't error |
| **Unrecognized preset name** (Q13) | Treat as free-text, log warning listing valid presets |
| **Prefetched content filtering** (Q5 from SpecFlow) | `filter_blocked_urls()` applied to search results before `_split_prefetched()`, so prefetched blocked content is also filtered |

## System-Wide Impact

- **Interaction graph:** YAML parsing → `ContextProfile` → carried on `ContextResult` → read by `agent.py` → passed to `search.py` (blocked), `relevance.py` (preferred), `synthesize.py` (tone), `agent.py` (gap_schema fallback)
- **Error propagation:** Malformed optional profile fields (bad type for `blocked_domains`, etc.) → `logger.warning()` → field defaults to empty → research continues with partial/no profile. This preserves the existing tolerant `_parse_template()` contract ("never raises — returns `(raw, None)` on any error"). Missing gap_schema file → `logger.warning()` → research continues without gaps
- **State lifecycle risks:** None — all new fields are read-only configuration. No persistent state changes
- **API surface parity:** MCP `list_contexts` tool already exists. No new MCP tools needed, but MCP instructions string needs updating if behavior changes. New fields are transparent — they affect pipeline behavior, not MCP interface

## Acceptance Criteria

- [ ] `ContextProfile` frozen dataclass in `context_result.py` with 4 fields
- [ ] `_parse_template()` extracts new fields from YAML frontmatter
- [ ] Fields sanitized at parse boundary (once, never double-sanitized)
- [ ] `filter_blocked_urls(results, blocked_domains)` helper in `search.py`
- [ ] Blocked domain filter applied at ALL search entry points (pass1, pass2, sub-queries, iteration, coverage retry)
- [ ] Subdomain matching: `example.com` blocks `sub.example.com` but not `notexample.com`
- [ ] `preferred_domains` parsed and stored on `ContextProfile` but no pipeline effect (deferred — see rationale)
- [ ] `gap_schema` path validated (no `..`, no absolute), resolved relative to project root
- [ ] `gap_schema` used as fallback when `self.schema_path` is None (no CLI `--schema` flag this cycle)
- [ ] Tone presets (`executive`, `technical`, `casual`) defined as constants
- [ ] Tone injected into `synthesize_report()` and `synthesize_final()` only
- [ ] Free-text tone sanitized + wrapped in `<tone_instruction>` XML tag
- [ ] `--list-contexts` CLI flag shows name + configured field summary
- [ ] `pfe.md` updated with example profile fields
- [ ] Tests for: parsing (valid, missing, malformed + tolerant defaults), domain filtering, domain matching, tone injection, gap_schema resolution, --list-contexts output, `list_available_contexts()` shape regression
- [ ] All existing tests pass (920+)

## Implementation Phases

### Session 1: Data Model + Parsing (~80 lines)

**Files:** `context_result.py`, `context.py`

**Tasks:**
1. Add `ContextProfile` frozen dataclass to `context_result.py`
2. Add `profile: ContextProfile | None = None` field to `ContextResult`
3. Update `ContextResult.loaded()` factory to accept `profile` parameter
4. Extend `_parse_template()` in `context.py` to extract new YAML fields **tolerantly** (preserving the existing "never raises" contract — `context.py:49`):
   - `preferred_domains` → `tuple[str, ...]` (sanitize each, convert list to tuple). If wrong type → `logger.warning()`, default `()`
   - `blocked_domains` → `tuple[str, ...]` (same). If wrong type → `logger.warning()`, default `()`
   - `gap_schema` → `str` (validate: no `..`, no absolute path). If invalid → `logger.warning()`, default `""`
   - `synthesis_tone` → `str` (sanitize). If wrong type → `logger.warning()`, default `""`
   - **Contract:** Malformed optional profile fields must NOT cause `_parse_template()` to return `(raw, None)` or `ContextResult.failed()`. The template and body parse normally; only the bad field defaults to empty. This matches the existing behavior where `context_usage` defaults to `""` if missing.
5. Validate `blocked_domains` ∩ `preferred_domains` overlap → `logger.warning()`
6. Construct `ContextProfile` and pass to `ContextResult.loaded()`
7. Update `pfe.md` with example fields

**Tests (~15):**
- Parse valid profile with all fields
- Parse profile with no new fields (backwards compatibility)
- Parse profile with partial fields (only blocked_domains)
- Malformed fields (blocked_domains as string instead of list) → field defaults to empty, template still parses
- Malformed profile field does NOT break template parsing (template returned, profile field just defaults)
- gap_schema path validation (reject `../`, absolute paths) → defaults to empty string
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

### Session 3: DEFERRED — Preferred Domains Boost

**Status:** Deferred from this cycle. The field is parsed and stored on `ContextProfile` (Session 1) but has no pipeline effect.

**Why deferred:** The original +0.5 boost is a no-op under current scoring. Scores are `int` (1-5), `relevance_cutoff` is `int` (3 in all modes). Score 2 + 0.5 = 2.5 → still < 3 → still drops. Score 3 already passes the `>= 3` gate without any boost. The +0.5 literally changes zero KEEP/DROP decisions.

**Alternatives considered and rejected:**
- **+1 boost:** Would rescue score-2 sources to score 3 (KEEP). Rejected — too aggressive. A source the LLM rated 2/5 for relevance shouldn't be kept just because it's from a preferred domain. That defeats the purpose of relevance gating.
- **Tiebreaker ordering:** When multiple sources have the same score, prefer preferred-domain sources. This changes ordering but not KEEP/DROP, so still no relevance-gate effect.
- **Lower cutoff for preferred domains:** e.g., cutoff 2 instead of 3. Rejected — creates a parallel gating path, adding complexity for unclear benefit.

**Future cycle options:** When a real use case emerges (e.g., configurable cutoff per profile, or a scoring model that produces float scores), revisit. The `preferred_domains` field is already on `ContextProfile` and will round-trip through parse/store correctly.

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
   - No CLI `--schema` flag exists and none is added this cycle — `gap_schema` is profile-only
2. **`--list-contexts` CLI flag** in `cli.py`:
   - Add `parser.add_argument("--list-contexts", action="store_true")`
   - Add early exit block (after `--list` check)
   - Add new `list_context_details()` helper in `context.py` (separate from `list_available_contexts()`):
     - For each context file, call `_parse_template()` to get full profile data
     - Returns richer metadata (name, profile fields summary)
     - Handle parse errors gracefully (return name + "parse error")
   - **Do NOT modify `list_available_contexts()`** — its `list[tuple[str, str]]` return shape is a stable contract used by `auto_detect_context()` and MCP `list_contexts`. Changing it would break both.
   - Implement `list_contexts_cli()` in `cli.py` using the new `list_context_details()`:
     - Display: name, configured fields (e.g., "blocked: 2 domains, tone: executive, gap_schema: gaps/pfe.yaml")

**Tests (~8):**
- gap_schema fallback when `self.schema_path` is None
- gap_schema missing file → warning, continues
- gap_schema path traversal rejection
- `list_context_details()` returns profile metadata
- `list_available_contexts()` unchanged — returns `(name, preview)` tuples (regression test)
- --list-contexts output format
- --list-contexts with no context files
- --list-contexts with parse error in one file

**Commit:** `feat(24-5): add gap_schema fallback and --list-contexts CLI`

## Alternative Approaches Considered

1. **Add fields to `ReportTemplate`** — Rejected: breaks every test that constructs `ReportTemplate`, mixes report-structure and pipeline-behavior concerns
2. **Store profile data directly on `ContextResult`** (flat fields) — Rejected: clutters an already 5-field dataclass. A separate `ContextProfile` is cleaner and more extensible
3. **Filter blocked domains in `fetch.py`** — Rejected: too late — we'd still waste search result slots on blocked URLs. Filtering in `search.py` (post-search, pre-fetch) is the right level
4. **Change `SourceScore.score` to `float`** — Not needed: `preferred_domains` deferred from this cycle. Would have rippled through logging, display, gate comparison

## Dependencies & Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Missing a search entry point for blocked_domains | HIGH | SpecFlow identified 6 sites. Grep for all `search(` and `_search_sub_queries` calls. Test with a blocked domain in deep mode |
| preferred_domains deferred — no pipeline effect | LOW | Field parsed/stored but no boost applied. Avoids the no-op problem (+0.5 on int scores/cutoff changes nothing). Re-evaluate when scoring or cutoff model changes |
| Tone prompt injection | LOW | Context files are trusted-author input. `sanitize_content()` + XML tag boundary provides adequate defense. Same trust level as existing `context_usage` field |
| Breaking existing tests | MEDIUM | `ContextProfile` has all-default fields. `ReportTemplate` unchanged. `ContextResult.loaded()` gets a new optional kwarg. Existing callers unaffected |

## Success Metrics

- All 920+ existing tests pass
- ~43 new tests covering parsing, blocked domains, tone, gap_schema, and CLI
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

## Deferred: preferred_domains

`preferred_domains` is parsed and stored on `ContextProfile` but has **no behavioral effect** this cycle. The +0.5 boost proposed in the brainstorm is a no-op under the current integer scoring model (scores 1-5 int, cutoff 3 int). See Session 3 for full analysis and rejected alternatives.

**Future cycle trigger:** When scoring changes to float, or when configurable per-profile cutoffs are added, revisit this. The field round-trips through YAML → parse → `ContextProfile` → serialize correctly today.

## Revision Log

**v2 (2026-03-06):** Plan-only revision fixing four issues from code review:
1. `preferred_domains` +0.5 boost is a no-op on int scores with int cutoff → deferred (parsed/stored, no pipeline effect)
2. `--schema` CLI flag doesn't exist → removed all CLI-precedence language for `gap_schema`; it's profile-only this cycle
3. Plan said malformed fields → `ContextResult.failed()` → abort. This breaks the tolerant `_parse_template()` contract (`context.py:49`: "Never raises"). Fixed: malformed optional fields → `logger.warning()` → field defaults to empty → research continues
4. Plan said "update `list_available_contexts()` if needed". This would break `auto_detect_context()` and MCP `list_contexts` which depend on the `(name, preview)` return shape. Fixed: add new `list_context_details()` helper instead; `list_available_contexts()` is untouched

## Feed-Forward

- **Hardest decision:** Deferring `preferred_domains` pipeline effect. The brainstorm assumed a +0.5 boost would work, but code analysis proved it's a no-op with integer scores and integer cutoff. Every alternative (+1 boost, parallel cutoff, tiebreaker) was either too aggressive or had no gate effect.
- **Rejected alternatives:** +1 boost (rescues bad sources), changing cutoff to float (complex for unclear benefit), `--schema` CLI flag (adds scope for a feature that works fine as profile-only), modifying `list_available_contexts()` return shape (breaks auto-detect + MCP).
- **Least confident:** Session 2's blocked_domains coverage across all 6+ search entry points. SpecFlow identified the sites, but the actual `agent.py` plumbing is complex with deep/standard/quick branching. The work session should grep for ALL search calls and verify each one gets the filter. If one is missed, blocked content leaks through in specific modes.
