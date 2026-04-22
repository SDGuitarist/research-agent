---
title: "Cycle 30: Summarization & Context Preservation"
date: 2026-04-21
status: complete
---

# Cycle 30: Summarization & Context Preservation

## What We're Building

Four features that preserve signal through the middle of the pipeline, now that upstream filters (C27-29) ensure the input is clean:

1. **Source diversity gate** — After scoring, count distinct domains among passing sources. Require minimum unique domains (2/3/4 by mode). If unmet, downgrade to short_report.
2. **Cross-chunk context** — Pass chunk index, total chunks, and a one-sentence prior-chunk summary to each summarization call.
3. **Sentence-boundary truncation** — Replace character-level truncation with sentence-boundary truncation. Add structured marker with percentage removed.
4. **Synthesis abstention gate** — At synthesis time, instruct the model to flag uncorroborated specific claims (stats, dates, named studies) rather than presenting as confirmed.

## Why This Approach

The entropy roadmap (C27-31) is dependency-ordered. Cycles 27-29 cleaned up inputs and outputs. Cycle 30 preserves signal in the middle — the summarization and truncation stages where information is compressed and can be silently lost.

**Why now:** With relevance cutoff at 4, snippet tiering, and skeptic enforcement in place, the sources reaching summarization are already vetted. These features preserve the quality that earlier cycles established.

## Key Decisions

### Abstention gate placement: synthesis, not summarization
The abstention gate lives in `synthesize.py` (or the synthesis prompt), not `summarize.py`. Reason: summarization happens per-chunk with no cross-source visibility. The model can't know if a claim is "uncorroborated" when it only sees one source's text. At synthesis time, all summaries are visible — the model can cross-reference.

**Evidence:** Epistemic calibration study section 3.5 — model refused fabricated citations when given cross-source context. Per-source summarization lacks this context, risking false refusals.

### Diversity gate: pure domain count, no reputation logic
Simple threshold: count unique domains among surviving sources after scoring but before the existing gate decision in `compute_gate_decision()`. Minimum: 2 (quick), 3 (standard), 4 (deep). If unmet, override the gate decision to `short_report`. No exception list for "trusted" domains.

**Rationale:** YAGNI. Domain reputation scoring is a C33+ concern if ever needed. Pure count is simple, testable, and addresses the entropy finding (single-domain reports lack cross-validation).

### Cross-chunk context: one-sentence summary only
Each chunk summarization call receives: chunk index (1-based), total chunk count, and a one-sentence summary of the previous chunk (~50 extra tokens). No bullet lists, no multi-chunk context.

**Rationale:** Roadmap spec. Linear growth with chunk count is unnecessary for 3-5 chunks per source. One sentence is enough to prevent "as mentioned above" artifacts and maintain coherence.

### Sentence-boundary truncation: regex-based, no NLP dependency
Replace `text[:max_chars]` with a regex that finds the last sentence boundary (`.` followed by space or end) before the character limit. No nltk or spacy dependency.

**Rationale:** The truncation function runs on already-extracted text, not raw HTML. Sentence boundaries are reliably marked by `. ` in clean text. Adding an NLP dependency for this is overkill.

## Existing Code Surface

| Feature | Module | Existing helper | Change type |
|---------|--------|-----------------|-------------|
| Diversity gate | `relevance.py` | `_extract_domain()` exists (line 136) | Extend — aggregate domain counts after scoring |
| Cross-chunk context | `summarize.py` | `summarize_chunk()` (line 73) | Modify — add params, update prompt |
| Sentence truncation | `token_budget.py` | `truncate_to_budget()` (line 143) | Replace — character-level → sentence-boundary |
| Abstention gate | `synthesize.py` | N/A — new instruction block | Add — synthesis prompt instruction (flag format TBD in plan: label vs. section) |

## Open Questions

*None — all resolved during brainstorm.*

## Resolved Questions

1. **Abstention gate placement?** → Synthesis (all summaries visible, cross-source context)
2. **Domain reputation exceptions?** → No, pure count (YAGNI)
3. **Cross-chunk context depth?** → One-sentence summary of previous chunk only
4. **Sentence detection method?** → Regex, no NLP dependency

## Feed-Forward

- **Hardest decision:** Abstention gate placement. Both options had real trade-offs (early catch vs. cross-source context). The epistemic calibration study tipped it toward synthesis.
- **Rejected alternatives:** Per-chunk abstention (false refusal risk without cross-source context), domain reputation exception list (YAGNI), multi-chunk context summaries (token growth for marginal benefit).
- **Least confident:** Whether the one-sentence prior-chunk summary is sufficient for deep-mode sources with 5+ chunks. If chunk summaries still show "as mentioned previously" artifacts after C30, a richer context may be needed in C33.

## Three Questions

1. **Hardest decision in this session?** Abstention gate placement. The roadmap flagged 75% confidence and said "planning must resolve." Cross-source context at synthesis is the right call, but it means uncorroborated claims survive through summarization unchanged — they're only flagged in the final report.
2. **What did you reject, and why?** Domain reputation exceptions. It's tempting to say "Wikipedia alone is fine" but that's a slippery slope toward maintaining a reputation list. Pure count is more honest about what the gate actually checks: did we look at more than one perspective?
3. **Least confident about going into plan?** The interaction between the diversity gate and C28's relevance cutoff. If 3 of 5 sources are from the same domain, they might all score 4+ individually but the diversity gate would still downgrade. This could increase short_report frequency. The plan needs to verify this with test scenarios.
