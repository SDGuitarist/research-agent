---
title: "Cycle 30: Summarization & Context Preservation"
type: feat
status: active
date: 2026-04-21
origin: docs/brainstorms/2026-04-21-cycle-30-summarization-context-preservation-brainstorm.md
feed_forward:
  risk: "Diversity gate + C28 relevance cutoff interaction may increase short_report frequency"
  verify_first: false
---

# Cycle 30: Summarization & Context Preservation

## Enhancement Summary

**Deepened on:** 2026-04-21
**Agents used:** 4 implementation researchers, architecture strategist, performance oracle

### Key Improvements from Deepening
1. **Diversity gate placement corrected** — runs AFTER `compute_gate_decision()` as post-decision downgrade, not before. Coverage retry path also gets the check.
2. **Sentence truncation uses `rfind()` not regex** — matches existing `_chunk_text()` tiered fallback pattern (paragraph → sentence → line → word → char). Simpler, faster, no backtracking risk.
3. **Chunk failure handling specified** — if `summarize_chunk()` returns `None`, pass `prior_summary=""` to next chunk (graceful degradation).
4. **No budget registration needed for abstention** — `instructions` component has priority 7 (never pruned). ~80 tokens in a 100K window is negligible.
5. **`check_domain_diversity()` extracted as standalone function** — testable in isolation, reusable in retry path.

## Prior Phase Risk

> "Least confident about going into plan? The interaction between the diversity gate and C28's relevance cutoff. If 3 of 5 sources are from the same domain, they might all score 4+ individually but the diversity gate would still downgrade. This could increase short_report frequency."

**How this plan addresses it:** Session 1 tests include a scenario where 4 sources from 2 domains all score 4+ in standard mode (min_unique_domains=3). The gate should downgrade to short_report. This is correct behavior — the diversity gate is intentionally stricter. If real-world usage shows excessive downgrades, the thresholds (2/3/4) are constants easily tuned.

## Overview

Four features that preserve signal through the middle of the pipeline. Each is independent and gets its own session/commit. Order: diversity gate first (affects which sources reach synthesis), then cross-chunk context and sentence truncation (independent of each other), then abstention gate last (operates on all prior improvements).

## What Exactly Is Changing

| Session | Module | Function | Change |
|---------|--------|----------|--------|
| 1 | `relevance.py`, `modes.py` | `evaluate_sources()`, mode factories | Add `min_unique_domains` field + domain diversity check after scoring |
| 2 | `summarize.py` | `summarize_chunk()`, `summarize_content()` | Add chunk index/total/prior params, sequential within-source processing |
| 3 | `token_budget.py` | `truncate_to_budget()` | Sentence-boundary regex + percentage marker |
| 4 | `synthesize.py`, `evidence.py` | `synthesize_report()`, `synthesize_final()` | Abstention instruction for uncorroborated single-source claims |

## What Must Not Change

- Existing gate behavior for sources that pass diversity (full_report / short_report / insufficient_data logic unchanged)
- Chunk summarization quality for single-chunk sources (no context header when chunk_index=1 and total_chunks=1)
- Truncation behavior when text fits within budget (no truncation = no change)
- `synthesize_draft()` must NOT receive abstention instruction (draft is factual extraction, not analytical)
- Existing `<skeptic_findings>`, `<critical_findings>`, and evidence-tier blocks unchanged

## Implementation Sessions

### Session 1: Source Diversity Gate (~55 lines)

**Files:** `modes.py`, `relevance.py`, `tests/test_relevance.py`

1. Add `min_unique_domains: int` field to `ResearchMode` frozen dataclass (after `relevance_cutoff`, line ~27)
   - `quick()`: 2, `standard()`: 3, `deep()`: 4
   - Add `__post_init__` validation: `min_unique_domains >= 1`
2. Extract `check_domain_diversity(surviving_urls: list[str], min_domains: int) -> tuple[bool, int]` as a standalone pure function in `relevance.py`
   - Returns `(passed, unique_count)` — testable in isolation, reusable in retry path
3. In `evaluate_sources()`, AFTER `compute_gate_decision()` (line ~421) — as a post-decision downgrade:
   - Call `check_domain_diversity()` on surviving source URLs
   - If diversity fails AND initial decision is `FULL_REPORT`: override to `SHORT_REPORT`
   - Append to rationale: "Downgraded: {n} unique domains < {min} required"
   - Log domain counts at INFO level
   - Note: diversity check runs AFTER the gate decision exists, not before
4. In `_try_coverage_retry()` (agent.py line ~784): apply same diversity check after merged evaluation to prevent retry bypass
5. Add `min_unique_domains` to `ModeInfo` dataclass and `list_research_modes` MCP output

**Tests (~8):**
- 4 sources from 4 domains, standard mode → no downgrade (passes diversity)
- 4 sources from 2 domains, standard mode (min=3) → downgrade to short_report
- 2 sources from 2 domains, quick mode (min=2) → no downgrade
- 1 source from 1 domain, quick mode (min=2) → downgrade
- Already short_report decision → diversity gate does NOT downgrade further to insufficient_data
- Already insufficient_data → diversity gate is a no-op
- Domain extraction from various URL formats (subdomains treated as same domain? No — `_extract_domain` returns netloc, so `blog.example.com` ≠ `www.example.com`. Document this.)
- ModeInfo includes min_unique_domains field
- Coverage retry path also applies diversity check (not bypassed)

**Commit:** `feat(30-1): source diversity gate with per-mode domain thresholds`

### Session 2: Cross-Chunk Context (~45 lines)

**Files:** `summarize.py`, `tests/test_summarize.py`

1. Add params to `summarize_chunk()`: `chunk_index: int = 1`, `total_chunks: int = 1`, `prior_summary: str = ""`
2. When `total_chunks > 1` and `chunk_index > 1` and `prior_summary`:
   - Prepend context header to user prompt: `"This is chunk {chunk_index} of {total_chunks}. Previous chunk covered: {sanitize_content(prior_summary)}"`
3. Add private helper `_extract_prior_context(summary: Summary, max_chars: int = 150) -> str`
   - Extract first sentence (up to first `. ` or `.\n`) capped at `max_chars`
   - If no sentence boundary, take first `max_chars` + "..."
4. In `summarize_content()`:
   - Change from concurrent `asyncio.gather()` to sequential loop for chunks
   - After each chunk, call `_extract_prior_context()` on the result
   - Pass as `prior_summary` to the next chunk
   - If a chunk returns `None` (API error): set `prior_summary=""` and continue — subsequent chunks degrade to current behavior (no context)
   - Single-chunk sources: no change (defaults apply, no context header)
   - Add timing log: `logger.info("Source %s: %d chunks in %.1fs", url, len(chunks), elapsed)`

**Key design note:** Sequential within a source (1-3 chunks), concurrent across sources (semaphore). Latency impact: ~1-2 extra API calls per multi-chunk source. Acceptable — deep mode has max 5 chunks per source.

**Tests (~6):**
- Single-chunk source: no context header in prompt
- Multi-chunk source: chunk 2 prompt includes "Previous chunk covered:"
- Prior summary is sanitized (prompt injection defense)
- Chunk index and total_chunks are correct (1-indexed)
- summarize_all() still processes multiple sources concurrently
- Result quality: multi-chunk summaries don't contain "as mentioned above" artifacts (hard to test mechanically — note for live validation)

**Commit:** `feat(30-2): cross-chunk context with prior summary threading`

### Session 3: Sentence-Boundary Truncation (~40 lines)

**Files:** `token_budget.py`, `tests/test_token_budget.py`

1. Replace `text[:max_chars]` with tiered boundary detection using `str.rfind()` (matches existing `_chunk_text()` pattern — no regex):
   - Priority 1: `text.rfind("\n\n", 0, max_chars)` (paragraph break)
   - Priority 2: `text.rfind(". ", 0, max_chars)` or `text.rfind(".\n", 0, max_chars)` (sentence end)
   - Priority 3: `text.rfind("\n", 0, max_chars)` (line break)
   - Priority 4: `text.rfind(" ", 0, max_chars)` (word break)
   - Priority 5: `text[:max_chars]` (character-level fallback)
   - Each priority requires using at least 60% of budget to prevent aggressive truncation
2. Update marker to include percentage removed:
   - `\n\n[Content truncated — {pct}% removed to fit token budget]`
   - `pct = round((1 - len(truncated) / len(original)) * 100)`

**Tests (~6):**
- Text with clear sentence boundaries: truncates at last sentence before limit
- Text with no periods: falls back to character-level truncation
- Very short text within budget: no truncation, no marker
- Percentage calculation: 50% of text removed → marker says "50% removed"
- Edge case: period at exact boundary → include the sentence
- Marker format matches expected string

**Commit:** `feat(30-3): sentence-boundary truncation with percentage marker`

### Session 4: Synthesis Abstention Gate (~35 lines)

**Files:** `evidence.py`, `synthesize.py`, `tests/test_synthesize.py`

1. Add `ABSTENTION_INSTRUCTION` constant to `evidence.py`:
   - "When presenting a specific factual claim (statistic, date, named study, direct quote) found in only one source, qualify it with explicit source attribution (e.g., 'according to Source N' or 'Source N reports'). Do not present single-source specific claims as established fact. General analysis and inferences drawn from multiple sources do not require this qualification."
2. Append `ABSTENTION_INSTRUCTION` to `mode_instructions` in `synthesize_report()` (after EVIDENCE_TIER_INSTRUCTION)
3. Add `ABSTENTION_INSTRUCTION` to `synthesize_final()` instructions block (after EVIDENCE_TIER_INSTRUCTION, before cite-sources line)
4. Do NOT add to `synthesize_draft()` (draft is factual extraction)

**Design choice:** No new inline label — the instruction is about phrasing ("according to Source N") not labeling. This avoids label proliferation and works with the existing evidence-tier system (a claim can be `[Documented]` from one source and still need source attribution).

**Tests (~5):**
- ABSTENTION_INSTRUCTION appears in synthesize_report() prompt
- ABSTENTION_INSTRUCTION appears in synthesize_final() prompt
- ABSTENTION_INSTRUCTION does NOT appear in synthesize_draft() prompt
- Instruction mentions "single source" qualification
- Integration: abstention + evidence tiers + critical findings all coexist in synthesize_final() prompt

**Commit:** `feat(30-4): synthesis abstention gate for single-source claims`

## Acceptance Tests

### Happy Path
- WHEN a standard-mode query returns 4 sources from 4 unique domains scoring 4+ THE SYSTEM SHALL produce a full_report with no diversity downgrade
- WHEN a deep-mode query returns summaries with 3 chunks THE SYSTEM SHALL pass chunk index and prior-chunk summary to chunks 2 and 3
- WHEN truncation is needed THE SYSTEM SHALL cut at the last sentence boundary and report percentage removed
- WHEN synthesis runs with all C30 features THE SYSTEM SHALL include abstention instruction, evidence tiers, and diversity rationale in the prompt

### Error Cases
- WHEN 4 standard-mode sources come from only 2 domains THE SYSTEM SHALL downgrade to short_report with rationale "Downgraded: 2 unique domains < 3 required"
- WHEN a text has no sentence boundaries (no periods) THE SYSTEM SHALL fall back to character-level truncation
- WHEN a single-chunk source is summarized THE SYSTEM SHALL NOT include context header (no "chunk 1 of 1" noise)
- WHEN synthesize_draft is called THE SYSTEM SHALL NOT include abstention instruction

### Verification Commands
- `python3 -m pytest tests/ -v` — all tests pass (1070+ baseline)
- `python3 -m pytest tests/test_relevance.py -k "diversity" -v` — diversity gate tests
- `python3 -m pytest tests/test_summarize.py -k "chunk_context" -v` — cross-chunk tests
- `python3 -m pytest tests/test_token_budget.py -k "sentence" -v` — truncation tests
- `python3 -m pytest tests/test_synthesize.py -k "abstention" -v` — abstention tests

## Dependencies & Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Diversity gate increases short_report frequency | MEDIUM | Thresholds (2/3/4) are constants, easily tuned. Test with representative queries post-deploy. |
| Sequential chunk processing adds latency | LOW | 1-2 extra API calls per multi-chunk source. Most sources are single-chunk. Deep mode max 5 chunks. |
| Sentence regex misses abbreviations (e.g., "Dr. Smith") | LOW | Regex matches `. ` (period + space) or `.\n`. Most abbreviations don't have trailing space before the next sentence. Edge cases fall back to character-level. |
| Abstention instruction causes over-qualification | LOW | Instruction explicitly exempts "general analysis and inferences from multiple sources." |
| Subdomain != domain (`blog.example.com` ≠ `www.example.com`) | LOW | `_extract_domain()` returns `netloc` which includes subdomains. This is intentionally conservative — subdomains are different editorial contexts. Document in code comment. |

## Feed-Forward

- **Hardest decision:** Whether to add a new inline label `[Uncorroborated]` or use phrasing guidance ("according to Source N"). Chose phrasing — it's less disruptive to the evidence-tier system and produces more natural reports. A label would need parsing support in C33.
- **Rejected alternatives:** (1) New `[Uncorroborated]` label — label proliferation, needs C33 parser changes. (2) Subdomain normalization (strip `www.`, `blog.` etc.) — editorial diversity argument: blog.example.com may have different editorial standards than www.example.com. (3) Concurrent chunk processing with post-hoc context injection — complex, fragile, and max 5 chunks per source doesn't justify the engineering.
- **Least confident:** Whether the one-sentence prior-chunk summary (first sentence or first 100 chars) provides enough context. If chunk 3 summaries still contain orphaned references in deep-mode testing, may need to pass a cumulative summary instead of just the prior chunk.

## Three Questions

1. **Hardest decision in this session?** Abstention gate design — label vs. phrasing instruction. Labels are consistent with C29's evidence tiers but create parser debt. Phrasing guidance is lighter and produces more natural text.
2. **What did you reject, and why?** Subdomain normalization. `blog.example.com` and `www.example.com` could have different editorial teams and perspectives. Treating them as the same domain would undercount actual diversity.
3. **Least confident about going into work?** Sequential chunk processing in `summarize_content()`. The current `asyncio.gather()` is clean and fast. Changing to a sequential loop within each source adds latency and complexity. If the one-sentence summary doesn't noticeably improve chunk coherence, this change has negative ROI.

## Codex Work Review Handoff

```
Read these files first for project context:
  - HANDOFF.md
  - CLAUDE.md

Review branch main against docs/plans/2026-04-21-cycle-30-summarization-context-preservation-plan.md.

Focus on:
1. Does the diff match the plan? Flag anything added or missing.
2. Does the diversity gate correctly count unique domains AFTER scoring
   and BEFORE the existing gate decision?
3. Does the diversity gate only downgrade full_report → short_report,
   never short_report → insufficient_data?
4. Is cross-chunk context sequential within a source but concurrent
   across sources? Verify the semaphore still limits global concurrency.
5. Does sentence-boundary truncation fall back to character-level when
   no sentence boundary exists?
6. Does abstention instruction appear in synthesize_report() and
   synthesize_final() but NOT synthesize_draft()?
7. Feed-Forward risk: does the diversity gate interact correctly with
   the relevance cutoff (4 in standard/deep)? Test scenario: 4 sources
   from 2 domains all scoring 4+ → should downgrade to short_report.

Key files changed: relevance.py, modes.py, summarize.py, token_budget.py,
  synthesize.py, evidence.py
Plan doc: docs/plans/2026-04-21-cycle-30-summarization-context-preservation-plan.md

Output: findings ordered by severity + a Claude Code fix prompt.
```
