---
title: "Cycle 27: Input Validation + Generation Controls"
date: 2026-03-25
origin: docs/research/2026-03-09-entropy-fixes-roadmap.md
cycle: 27
theme: "Prevent bad data from entering the pipeline. Tune generation knobs."
prior_lessons:
  - docs/solutions/security/non-idempotent-sanitization-double-encode.md
  - docs/solutions/architecture/tiered-model-routing-planning-vs-synthesis.md
---

# Cycle 27: Input Validation + Generation Controls

## Prior Phase Risk

> "Pre-summary abstention gate placement (C30). 75% confidence." — HANDOFF.md

This risk is for C30, not C27. No unverified blocker for this cycle.

## What We're Building

Three features that harden the pipeline's input boundary and stabilize LLM output:

### 1. Vague Query Detection (`decompose.py`)

A pre-decomposition gate that rejects queries too vague to produce useful research.

- **Where:** Before the LLM call in `decompose.py` (before line 87's `sanitize_content(query)`)
- **Rule:** Reject if fewer than 3 meaningful words after stripping stopwords. Single proper nouns (e.g., "Tesla", "Anthropic") pass via a capitalization heuristic — no NLP dependency needed.
- **Behavior:** Raise a custom `VagueQueryError` caught by the CLI. Clean exit, user-friendly message, zero API calls wasted
- **Test cases:** "stuff", "things", "what's up" rejected; "San Diego wedding venues" accepted; "climate change impacts on agriculture" accepted
- **Edge case:** Single proper nouns like "Tesla" or "Anthropic" should pass — they have research intent despite being one word. A capitalization heuristic (starts with uppercase, not start of sentence) is cheap and catches most cases without NLP

### 2. Idempotent Sanitization (`sanitize.py`)

Replace the manual `.replace()` chain with `html.escape()` to fix the known double-encoding bug.

- **What changes:** `sanitize_content()` body becomes `return html.escape(text, quote=False)` (stdlib `html` module). Using `quote=False` escapes only `&`, `<`, `>` — matching current behavior. The default (`quote=True`) would also escape `"` to `&quot;`, which is a behavioral change we don't need.
- **Why:** `html.escape()` handles `&`, `<`, `>` in the correct order and is idempotent — calling it twice produces the same output. The current manual chain turns `&` into `&amp;` then `&amp;amp;` on a second call.
- **Call-site changes:** None. Same signature `(str) -> str`. ~30 call sites untouched.
- **Prior lesson:** `non-idempotent-sanitization-double-encode.md` — sanitize ONCE at the boundary, document "pre-sanitized by X" at consumption sites. The `synthesize.py:583` double-sanitize risk becomes a non-issue once the function is idempotent.
- **Test:** Assert `sanitize_content(sanitize_content(x)) == sanitize_content(x)` for a corpus including `&`, `<`, `>`, `"`, `'`, `AT&T`, and already-escaped strings like `&amp;`
- **Note:** Using `quote=False` avoids the `"` → `&quot;` behavioral change. If we later need `"` escaping, switch to `quote=True` — but for now, minimize diff from current behavior.

### 3. Per-Task Temperature Controls (`modes.py` + ~15 call sites)

Add temperature fields to `ResearchMode` and pass them to every `messages.create()` call.

- **New fields on `ResearchMode`:** `planning_temperature: float`, `summarize_temperature: float`, `synthesis_temperature: float`
- **Defaults (from roadmap):**
  - `planning_temperature: 0.2` — for decompose, relevance scoring, context auto-detect, query refinement
  - `summarize_temperature: 0.5` — for chunk summarization
  - `synthesis_temperature: 0.8` — for report synthesis, skeptic lenses, critique, follow-up generation
- **Routing rule:** Each call site picks the temperature that matches its task type, not its model. Classification tasks get `planning_temperature` regardless of whether they use Haiku or Sonnet.
- **Call sites (~15):** decompose.py, relevance.py (x3), context.py, iterate.py (x2), coverage.py, critique.py (x2), skeptic.py, summarize.py, search.py, synthesize.py (x2+)
- **Prior lesson:** `tiered-model-routing-planning-vs-synthesis.md` — route by task type, not cost. Same principle applies to temperature.
- **Mode overrides:** Each mode (quick/standard/deep) uses the same defaults initially. Deep mode may want higher synthesis_temperature later, but YAGNI — start with uniform defaults across modes.

## Why This Approach

- **Vague query gate as error, not auto-refine:** Zero API cost for garbage input. The user is right there at the CLI — asking them to rephrase is faster and cheaper than an LLM round-trip to guess what they meant.
- **html.escape() over a guard pattern:** Stdlib, battle-tested, idempotent by design. Adding a "was this already sanitized?" flag introduces a new failure mode (flag set incorrectly) that's worse than the problem it solves.
- **Temperature on ResearchMode, not a separate map:** Follows the existing pattern (model fields are already on ResearchMode). No new abstractions. Frozen dataclass means modes are still immutable and testable.

## Key Decisions

1. Vague queries raise `VagueQueryError` — clean exit, no API calls
2. `html.escape()` replaces manual `.replace()` chain — idempotent, stdlib
3. Three temperature tiers on `ResearchMode` — planning (0.2), summarize (0.5), synthesis (0.8)
4. Temperature routes by task type, not model — same principle as tiered model routing
5. Uniform temperature defaults across all modes (quick/standard/deep) to start

## Open Questions

None — all three features are well-specified in the roadmap and design decisions are resolved.

## Feed-Forward

- **Hardest decision:** Whether vague query detection should auto-refine with the LLM or just reject. Chose reject — it's cheaper, simpler, and the user is interactive at the CLI. Auto-refine is a feature for a future non-interactive mode.
- **Rejected alternatives:** (1) Already-sanitized guard pattern for sanitize.py — adds complexity and a new flag to maintain when html.escape() solves it for free. (2) Separate temperature map instead of fields on ResearchMode — violates the existing pattern where all generation params live on the mode dataclass. (3) Warn-and-continue for vague queries — defeats the purpose of a gate.
- **Least confident:** The proper-noun edge case in vague query detection. "Tesla" is one word but has clear research intent. A capitalization heuristic is the plan, but edge cases remain: all-lowercase brand names ("adidas"), acronyms ("NASA"), and queries that are short but valid ("AI ethics"). The plan phase should define the exact heuristic with a test corpus.
