# Cycle 28 Brainstorm: Relevance & Source Quality Gates

**Date:** 2026-04-05
**Roadmap ref:** `docs/research/2026-03-09-entropy-fixes-roadmap.md` (Cycle 28 section)

## What We're Building

Three changes to filter noise before it reaches synthesis:

1. **Raise relevance cutoff** from 3 to 4 for standard/deep modes (keep 3 for quick)
2. **Snippet quality tier** — structured `source_tier` field on `Summary`, cap snippet scores at 3
3. **Quick mode min sources** — raise `min_sources_short_report` from 1 to 2; return `insufficient_data` when only 1 source survives

## Why This Approach

### Cutoff 3→4 for standard/deep

Currently all modes use `relevance_cutoff=3`. A score of 3/5 means "somewhat relevant" — these sources add noise to synthesis without strong evidence. Raising to 4 means only "clearly relevant" or "highly relevant" sources survive.

Quick mode keeps cutoff=3 because it has fewer sources to work with (4 max) and is designed for fast answers, not comprehensive research.

**Validation:** Quick manual A/B test with 10 queries — compare gate decisions at cutoff 3 vs 4. If any mainstream query flips from `full_report` to `short_report`, investigate. No formal env var scaffolding needed (Cycle 21 already proved Haiku scoring is stable).

**Prior art:** Cycle 21 A/B tested Haiku vs Sonnet relevance scoring with 9 queries — zero decision flips. The scoring model is stable. A 1-point cutoff bump on a stable scorer is low risk.

### Snippet quality tier on Summary

Snippet-sourced content (search snippet fallback in `cascade.py`) is already tagged with `[Source: search snippet]` text prefix, but there's no structured field. This means a snippet can score 4-5 and punch above its weight in the relevance gate.

**Approach:** Add `source_tier: str = "full"` to the `Summary` frozen dataclass. Set to `"snippet"` when content comes from snippet fallback. In `score_source()`, cap the final score at 3 when `source_tier == "snippet"`.

**Why Summary, not ExtractedContent:** Only the relevance scorer needs tier info today. Adding it to `ExtractedContent` (deeper in the pipeline) is more architecturally complete but violates YAGNI — the Cycle 24 "no forward-compatible stubs" pattern says add the field where it's needed, extend later if needed (~2 lines).

**Why not text prefix detection:** Checking `summary.startswith("[Source: search snippet]")` is fragile — any prefix text change silently breaks detection. Cycle 26 lesson: text conventions are brittle (word-boundary matching was added specifically to fix substring false positives).

### Quick mode min sources 1→2

Currently quick mode can produce a report from 1 surviving source. This risks presenting one website's claims as "research findings." Raising to 2 means at minimum 2 independent sources must pass relevance to generate any report.

When only 1 source survives: return `insufficient_data` response with the source URL, so the user can investigate directly. This is honest — a single-source "report" isn't research.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Cutoff per mode | 4 standard/deep, 3 quick | Quick has fewer sources; standard/deep benefit from stricter filtering |
| Snippet tier tracking | Field on `Summary` dataclass | Structured, testable, minimal change. Extend to `ExtractedContent` later if needed |
| Snippet score cap | Max 3 regardless of LLM score | Snippets are thin content — even if "relevant," they lack depth for high-quality synthesis |
| Quick mode 1-source behavior | Return `insufficient_data` | Honest. Single-source reports aren't research. User gets the URL to investigate. |
| A/B test approach | Quick manual check (10 queries) | Proportionate to the change. Haiku scoring is proven stable. Formal env var is overkill. |
| Score cap interaction with cutoff | Snippet score capped at 3, standard cutoff is 4 | Snippets are automatically excluded from standard/deep. Quick mode (cutoff=3) may still include them. This is intentional — quick mode tolerates thinner sources. |

## Interaction Effects

The three changes interact:

1. **Cutoff + snippet cap:** With standard/deep cutoff at 4 and snippet cap at 3, snippets are automatically excluded from standard/deep reports. Quick mode (cutoff=3) can still include snippets. This is a clean separation — quick mode is for speed and tolerates thinner sources.

2. **Snippet cap + quick min sources:** A quick mode query where 2 of 4 sources are snippet-only and score 3: they survive (cutoff=3), contributing to the 2-source minimum. The report is lower quality but not single-source. This is acceptable for quick mode.

## Estimated Sessions

3 sessions, matching the roadmap:
1. **Cutoff change + A/B test:** Change `relevance_cutoff` in `standard()` and `deep()` factory methods. Run 10-query manual A/B. Update `ModeInfo` if needed.
2. **Snippet tier:** Add `source_tier` to `Summary`, cap score in `score_source()`. How `source_tier` gets set is unresolved — plan phase must decide between detecting text prefix in `summarize_content()` (fragile) or adding a field to `ExtractedContent` and threading it (cleaner but more plumbing).
3. **Quick mode min sources:** Change `min_sources_short_report=2` in `quick()`. Verify `insufficient_data` path works correctly with 1 source. Update MCP docs if behavior changes.

## Feed-Forward

- **Hardest decision:** Whether snippet tier tracking belongs on `Summary` vs `ExtractedContent`. Chose `Summary` (YAGNI), but the brainstorm acknowledged this is a trade-off — if Cycle 29's evidence-tier labeling needs tier info in `synthesize.py`, we'll need to extend.

- **Rejected alternatives:** (1) Formal A/B testing with env var for cutoff change — disproportionate for a 1-point integer bump on a proven-stable scorer. (2) Text prefix detection for snippet tier — fragile, violates Cycle 26 lesson on text conventions. (3) Single-source quick reports with disclaimer — still risky, and "disclaimer" is the kind of advisory-not-enforced pattern the entropy audit flagged. (4) Cutoff=4 for all modes — quick mode needs the lower threshold due to fewer sources.

- **Least confident:** The snippet tier detection mechanism during summarization. Currently `summarize_content()` receives `ExtractedContent` objects, but snippet fallback tags content with a text prefix (`[Source: search snippet]`). To set `source_tier="snippet"` on `Summary`, we need to either: (a) detect the text prefix in `summarize_content()` and propagate, or (b) add a field to `ExtractedContent` and thread it. Option (a) re-introduces the text convention fragility we're trying to avoid. Option (b) is more work but cleaner. The plan phase should resolve this.
