---
title: "Skeptic Enforcement, Quality Gates, Evidence Tiers"
date: 2026-04-21
category: feature-implementation
tags: [prompt-engineering, adversarial-verification, quality-gate, evidence-labeling, regex-extraction, three-way-contract]
module: "skeptic.py, synthesize.py, search.py, agent.py, evidence.py"
cycle: 29
---

# Skeptic Enforcement, Quality Gates, Evidence Tiers

Cycle 29 addressed three entropy audit findings: skeptic findings weren't enforced in synthesis, LLM refinement ran on garbage-in snippets, and reports mixed documented facts with inferences without labeling. See `docs/plans/2026-04-21-cycle-29-skeptic-enforcement-plan.md` for design decisions.

## Risk Resolution

| Flagged Risk | What Actually Happened | Lesson |
|---|---|---|
| `[Critical Finding]` parsing fragility (plan risk #1) | Regex handles `[Critical Finding]`, `**[Critical Finding]**`, `[Evidence][Critical Finding]`, and em-dash separators. Combined-mode lens prefixes work because regex matches substring. | Coincidental correctness is fine IF you add regression tests proving it works. The tests are the safety net, not the regex design. |
| Quality gate thresholds are heuristic (plan risk #2) | 50-char (standard) and 100-char (deep) thresholds. 6 existing tests broke because mock data was too short. | Quality gates have a blast radius on existing tests. When adding a gate, grep for mock data that would trip it and fix preemptively. |
| Evidence-tier labels drift in long reports (plan risk #3) | Unverified — API key expired, live deep-mode test blocked. Mid-report reminder is the only mitigation. | Deferred verification must name the exact command and acceptance criterion. Documented in HANDOFF.md: run `--deep` query, check last 3 sections. |
| Token budget impact from tier instructions (review finding) | ~200 tokens added per prompt, not registered with `allocate_budget()`. No failures at current sizes. | New prompt instructions should be budget-registered. Watch in C30 for budget violations in deep-mode with long contexts. |

## Key Patterns

### 1. Three-Way Enforcement Contract

When the synthesis prompt says "address this finding," the model often claims it "incorporated" the concern without changing anything. The fix: give exactly three options, each a concrete action.

```python
skeptic_instruction += (
    "\n\nFor each numbered finding, you must do exactly one of:\n"
    "  (a) Remove the disputed claim from the report entirely.\n"
    "  (b) Mark the claim [Disputed] with a one-sentence reason.\n"
    "  (c) Cite additional evidence that directly addresses it.\n"
)
```

**When to apply:** Any prompt that requires the model to "address" or "respond to" a list of items. Vague instructions ("address this") produce vague compliance. Concrete action menus produce concrete actions.

### 2. Derive, Don't Thread Redundant Parameters

`synthesize_final()` already receives `skeptic_findings`. Instead of adding a `critical_findings` parameter:

```python
# Inside synthesize_final(), after building skeptic_block:
critical = extract_critical_findings(skeptic_findings)
if critical:
    numbered = "\n".join(
        f"{i}. {sanitize_content(f)}" for i, f in enumerate(critical, 1)
    )
    skeptic_block += f"\n<critical_findings>\n{numbered}\n</critical_findings>\n"
```

**When to apply:** When the data you need is already in an existing parameter. Adding a redundant parameter makes the interface look like the existing integration doesn't exist.

### 3. Snippet/Summary Quality Gate with Noun-Phrase Fallback

LLM query refinement needs meaningful input. When snippets or summaries are too short, the model hallucinates a refined query. The fix: check average length, fall back to stopword removal.

```python
avg_snippet_len = sum(len(s) for s in snippets) / max(len(snippets), 1)
if avg_snippet_len < 50:
    logger.info("Snippet quality below threshold, using noun-phrase fallback")
    refined_query = extract_noun_phrases(query)
else:
    refined_query = await asyncio.to_thread(refine_query, ...)
```

**When to apply:** Before any LLM call that takes prior-step output as context. If the context is empty or degenerate, skip the LLM call and use a deterministic fallback. Standard mode checks snippets (< 50 chars); deep mode checks summaries (< 100 chars) because deep mode has richer data at that point.

### 4. Vocabulary Module for Prompt Labels

Evidence-tier labels (`[Documented]`, `[Inferred]`, `[Illustrative]`, `[Speculative]`) are defined once in `evidence.py` and imported into synthesis prompts. The instruction and mid-report reminder are constants, not inline strings.

```python
# evidence.py — single source of truth
EVIDENCE_TIERS: tuple[str, ...] = ("Documented", "Inferred", "Illustrative", "Speculative")
EVIDENCE_TIER_INSTRUCTION = "Label every factual claim with one of these evidence tiers: ..."
EVIDENCE_TIER_REMINDER = "Remember: every factual claim must carry one of these ..."
```

**When to apply:** When the same vocabulary appears in multiple prompts. A shared constant prevents drift between the instruction ("label with these tiers") and the reminder ("remember to use these tiers").

## Prevention Checklist

1. When adding prompt enforcement, provide a concrete action menu (3-way contract), not "address this"
2. When adding a quality gate, grep test files for mock data that would trip the new threshold
3. When a parameter's data is already available inside the function, derive internally — don't add a redundant parameter
4. When adding new prompt instructions, register them with `allocate_budget()` or note the omission
5. When regex correctness is coincidental (works by substring matching), add regression tests covering the actual output format
6. When live validation is blocked, document the exact command and acceptance criterion in HANDOFF.md
7. When adding label vocabulary, put it in a dedicated module and import — don't inline strings across multiple prompts

## Open Questions / C30 Watch

- **Token budget:** Evidence-tier instructions (~200 tokens) not registered with `allocate_budget()`. Monitor deep-mode reports with long contexts.
- **Tier-label drift:** Unverified in deep-mode reports. Run live validation when API key is replaced. If labels absent in >50% of final sections, add per-section reminder.
- **Regex design:** `[Evidence][Critical Finding]` works by substring match, not intentional design. If skeptic prompt format changes, the regex may silently miss findings. The regression tests are the canary.

## Feed-Forward

- **Hardest decision:** The three-way enforcement contract wording. "Refute or incorporate" was the plan's original intent, but review correctly identified that models interpret "incorporate" as "mention without changing." The three concrete options (remove, mark [Disputed], cite evidence) force observable action.
- **Rejected alternatives:** Registering evidence-tier instructions with `allocate_budget()` now. The ~200 tokens are well within budget headroom, and registering would require touching the budget component map in two functions for negligible benefit. Deferred to C30 if budget violations appear.
- **Least confident:** Whether the mid-report reminder is sufficient for deep-mode reports. This is the same risk from the plan, still unverified. C33's post-synthesis extraction will be the definitive fix.

## Three Questions

1. **Hardest pattern to extract from the fixes?** The quality gate blast radius on existing tests. The pattern ("grep for mock data that would trip the new threshold") is obvious in retrospect but wasn't anticipated during planning. 6 tests broke because their mock snippets were 1-9 chars — the fix was mechanical but the discovery was not.
2. **What did you consider documenting but left out, and why?** The `STOP_WORDS` reuse decision (importing from `query_validation.py` instead of creating a new set in `search.py`). Left it out because it's a standard "don't duplicate constants" decision — not a pattern worth surfacing.
3. **What might future sessions miss that this solution doesn't cover?** The interaction between quality gates and the relevance gate. When the snippet quality gate fires, the noun-phrase fallback produces a simpler refined query, which may return fewer or lower-quality pass2 results, which then hit the relevance cutoff (raised to 4 in C28). The cascading effect could produce more `insufficient_data` responses than expected. No evidence this is happening yet, but it's an untested interaction.
