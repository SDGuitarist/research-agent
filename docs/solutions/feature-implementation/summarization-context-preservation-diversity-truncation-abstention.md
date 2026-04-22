---
title: "Summarization & Context Preservation: Diversity Gate, Cross-Chunk Context, Sentence Truncation, Abstention"
date: 2026-04-21
category: feature-implementation
tags: [diversity-gate, cross-chunk-context, sentence-truncation, abstention, quality-gate, rfind-fallback, sequential-async]
module: "relevance.py, summarize.py, token_budget.py, synthesize.py, evidence.py, modes.py, agent.py"
cycle: 30
---

# Summarization & Context Preservation

Cycle 30 addressed the middle of the pipeline — where information is compressed and can be silently lost. Four features preserve signal now that upstream filters (C27-29) ensure clean input. See `docs/plans/2026-04-21-cycle-30-summarization-context-preservation-plan.md` for design decisions.

## Risk Resolution

| Flagged Risk | What Actually Happened | Lesson |
|---|---|---|
| Diversity gate increases short_report frequency (plan risk #1) | Thresholds (2/3/4) are additive — only downgrades FULL_REPORT, never SHORT_REPORT→INSUFFICIENT_DATA. Existing retry test passed because `_make_summaries()` generates unique domains. | Test helpers that generate unique data may accidentally satisfy new gates. When adding a gate, also audit test helpers for unintentional compliance. |
| Sequential chunk processing adds latency (plan risk #2) | Implemented with timing log. Most sources are 1 chunk (no change). Deep mode max 5 sequential calls per source (~25s worst case on a 60-120s pipeline). | When changing concurrency model, add a timing log at the changeover point. Proves the impact without needing a separate benchmark. |
| Sentence truncation misses abbreviations (plan risk #3) | Used `rfind()` tiered fallback matching existing `_chunk_text()` pattern. No regex needed. Abbreviations ("Dr. Smith") only trigger if they're the *last* `. ` before the boundary — statistically unlikely. | Match existing patterns before inventing new ones. `_chunk_text()` already validated the paragraph→sentence→line→word→char fallback chain. |
| Abstention instruction causes over-qualification (plan risk #4) | Instruction explicitly exempts "general analysis and inferences from multiple sources." Phrasing-based ("according to Source N") not label-based. | When adding behavioral instructions to synthesis, include an explicit exemption for the common case. Without it, the model over-applies the rule. |
| MCP parity (review finding) | `min_domains=` missing from `list_research_modes()` output. Caught by Codex review. | MCP parity is the #1 recurring review finding (C19, 26, 27, 28, 30). When adding ResearchMode fields, update ModeInfo + list_modes() + list_research_modes in the same commit. |
| Chunk position header missing (review finding) | Plan specified "chunk {index} of {total}" but initial implementation only had "Previous chunk covered:". Fixed in review. | Read the plan literally during implementation. "Chunk index and total chunks" means two params, not just prior context. |

## Key Patterns

### 1. Post-Decision Downgrade Gate

The diversity gate runs AFTER `compute_gate_decision()`, not before. It can only tighten the decision (FULL_REPORT → SHORT_REPORT), never loosen or further downgrade.

```python
decision, rationale = compute_gate_decision(total_survived, total_scored, mode)

if decision == GateDecision.FULL_REPORT:
    diversity_passed, unique_count = check_domain_diversity(
        surviving_urls, mode.min_unique_domains,
    )
    if not diversity_passed:
        decision = GateDecision.SHORT_REPORT
        rationale += f" Downgraded: {unique_count} unique domains < {mode.min_unique_domains} required"
```

**When to apply:** When adding a new quality criterion that should be stricter than the existing gate but never produce a worse outcome than the existing gate would have chosen. The guard `if decision == FULL_REPORT` ensures the new gate only fires on the happiest path.

### 2. Standalone Pure Function for Reusable Gate Logic

`check_domain_diversity()` is extracted as a standalone function, not inlined in `evaluate_sources()`. This makes it testable in isolation and reusable in the coverage retry path.

```python
def check_domain_diversity(surviving_urls: list[str], min_domains: int) -> tuple[bool, int]:
    unique_domains = {_extract_domain(url) for url in surviving_urls}
    count = len(unique_domains)
    return count >= min_domains, count
```

**When to apply:** When the same gate logic needs to run in two code paths (initial evaluation + retry merge). Extract as pure function with simple inputs and tuple return.

### 3. Sequential-Within-Source, Concurrent-Across-Sources

Cross-chunk context requires sequential processing (chunk 2 needs chunk 1's summary). But sources are independent. The solution: sequential `for` loop within `summarize_content()`, semaphore preserved for cross-source concurrency in `summarize_all()`.

```python
for i, chunk in enumerate(chunks, 1):
    async with semaphore if semaphore is not None else contextlib.nullcontext():
        result = await summarize_chunk(
            ..., chunk_index=i, total_chunks=total_chunks,
            prior_summary=prior_context,
        )
        if isinstance(result, Summary):
            prior_context = _extract_prior_context(result)
        else:
            prior_context = ""  # graceful degradation
```

**When to apply:** When items within a group need ordering but groups are independent. The semaphore controls total concurrency; the loop controls within-group ordering. Key: if a step fails, reset context to empty and continue — don't propagate `None`.

### 4. Tiered rfind() Fallback for Boundary Detection

Sentence truncation uses `str.rfind()` with a priority chain, matching the existing `_chunk_text()` pattern — no regex needed.

```python
min_chars = int(max_chars * 0.6)
pos = truncated.rfind("\n\n", min_chars)          # paragraph
if pos == -1:
    pos = max(truncated.rfind(". ", min_chars),
              truncated.rfind(".\n", min_chars))   # sentence
if pos == -1:
    pos = truncated.rfind("\n", min_chars)          # line
if pos == -1:
    pos = truncated.rfind(" ", min_chars)           # word
# else: character-level fallback
```

**When to apply:** Any text boundary detection where natural breaks exist at multiple granularities. The 60% minimum prevents aggressive truncation (don't cut to a paragraph break at 10% of the budget). `rfind()` is O(n) with no backtracking risk.

### 5. Phrasing Instruction, Not Label Proliferation

The abstention gate uses phrasing guidance ("according to Source N") not a new inline label. This avoids creating parser debt for C33 and works alongside the existing evidence-tier labels.

```python
ABSTENTION_INSTRUCTION = (
    "When presenting a specific factual claim (statistic, date, named study, "
    "direct quote) found in only one source, qualify it with explicit source "
    "attribution. Do not present single-source specific claims as established "
    "fact. General analysis and inferences drawn from multiple sources do not "
    "require this qualification."
)
```

**When to apply:** When you want to change model behavior for a specific case without adding a new label/tag to the output format. Phrasing instructions are invisible to downstream parsers.

## Prevention Checklist

1. When adding a quality gate, audit test helpers (`_make_summaries`, `_make_evaluation`) for accidental compliance with the new threshold
2. When adding ResearchMode fields, update ModeInfo + list_modes() + list_research_modes in the SAME commit
3. When changing async concurrency (gather → sequential), add a timing log at the changeover point
4. When a step in a sequential chain fails, reset context and continue — don't propagate None
5. Before writing a regex for boundary detection, check if `rfind()` with a priority chain already exists in the codebase
6. When adding synthesis instructions, include an explicit exemption for the common case
7. Read the plan literally during implementation — "chunk index and total chunks" means two params

## Open Questions / C31+ Watch

- **One-sentence vs cumulative summary:** The prior-chunk context passes only the previous chunk's first sentence. If deep-mode chunk 3+ summaries show orphaned references in live testing, upgrade to cumulative summary. Unverified — API key still placeholder.
- **Diversity gate threshold tuning:** 2/3/4 may be too strict for niche topics with few authoritative sources. Monitor short_report frequency after API key renewal.
- **Abstention over-qualification:** Instruction exempts "general analysis" but borderline cases (single-source trends, single-source market analysis) may still get qualified. Monitor report quality.

## Feed-Forward

- **Hardest decision:** Post-decision downgrade design for the diversity gate. Placing the check AFTER `compute_gate_decision()` means the existing gate logic is untouched — the diversity gate only tightens, never loosens. This was non-obvious (initial plan said "before") and was corrected during deepening.
- **Rejected alternatives:** (1) Regex for sentence truncation — `rfind()` is simpler, faster, and matches existing code. (2) New `[Uncorroborated]` label for abstention — creates parser debt for C33. (3) Concurrent chunks with post-hoc context injection — complex for max 5 chunks. (4) Subdomain normalization — subdomains may have different editorial contexts.
- **Least confident:** Whether the diversity gate + relevance cutoff interaction produces too many short_report downgrades in practice. Standard mode requires 3 unique domains among 4+ surviving sources — for niche queries with few authoritative sites, this may be too strict.

## Three Questions

1. **Hardest pattern to extract from the fixes?** The "test helper accidental compliance" pattern. `_make_summaries()` generates example1.com, example2.com, etc. — unique by construction. The retry diversity test passed not because the gate was correct, but because the test data happened to satisfy it. The lesson: when adding gates, audit test *helpers*, not just test *assertions*.
2. **What did you consider documenting but left out, and why?** The `time.monotonic()` timing log in `summarize_content()`. It's a diagnostic, not a pattern — one line of code with obvious purpose. Not worth a section.
3. **What might future sessions miss that this solution doesn't cover?** The cascading interaction between all pipeline gates. C28 raised relevance cutoff to 4, C29 added snippet score cap at 3, C30 added diversity minimum. Each gate is correct in isolation, but their combined effect on a niche query with few sources hasn't been tested end-to-end. A query that returns 4 sources from 2 domains, with 2 being snippets (capped at 3, below cutoff 4), leaves only 2 surviving from 2 domains — passes diversity but hits short_report by count. The interaction is correct but unintuitive.
