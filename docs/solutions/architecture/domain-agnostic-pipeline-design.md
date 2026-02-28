---
title: Domain-Agnostic Pipeline Design
date: 2026-02-28
category: architecture
tags: [prompt-engineering, domain-independence, sanitization-boundary, hidden-defaults, relevance-gating]
module: summarize.py, synthesize.py, decompose.py, context.py, context_result.py, agent.py, critique.py
symptoms:
  - business-domain language in reports for non-business queries
  - auto-detect loads wrong context for unrelated queries
  - legacy fallback silently loads default file when user expects no context
  - "&amp;amp;" in critique guidance from double-sanitization between write and read
severity: medium
summary: >
  Removed hardcoded business-domain assumptions from 7 pipeline prompts,
  eliminated hidden default context path and single-file auto-detect short-circuit,
  and resolved write-time vs read-time sanitization boundary conflict. The pipeline
  now works for any context file without domain-specific bias.
commits: 10a8b75, 60a185a, 80d27ad, 341a3ab
---

# Domain-Agnostic Pipeline Design

**Cycle 22** | 2026-02-28

## Problem

The research pipeline had four categories of domain coupling that prevented it
from working cleanly with non-business context files:

1. **Domain-biased prompts** — Seven locations hardcoded business-analysis
   language ("KEY QUOTES from reviews/marketing", "TONE: persuasion approach",
   "business context", "positioning, threats, opportunities") regardless of the
   query or context file.

2. **Hidden default path** — `DEFAULT_CONTEXT_PATH = Path("research_context.md")`
   silently loaded a file when `context_path` was `None`, making the no-context
   case indistinguishable from the default-context case.

3. **Short-circuit bypass** — When `contexts/` had exactly one file,
   `auto_detect_context()` skipped the LLM relevance check and always loaded it.
   A query about Python asyncio got Pacific Flow Entertainment business context.

4. **Write-time sanitization** — `critique.py:205` sanitized strings before
   writing to YAML. When `_summarize_patterns()` in `context.py` read them back
   and sanitized again at the consumption boundary, ampersands double-encoded:
   `& → &amp; → &amp;amp;`.

## Root Cause

The pipeline was built for a single use case (competitive intelligence for
Pacific Flow Entertainment) and expanded to general research without auditing
the assumptions baked into prompts, defaults, and data flow.

### Why these four issues are connected

They all stem from **implicit domain assumptions**:

- The prompts assumed every query was business analysis
- The default path assumed you always wanted your one context file
- The short-circuit assumed one context file = always relevant
- The write-time sanitization assumed data wouldn't be re-sanitized at read time

Each assumption was reasonable when the system had one user and one context file.
They broke when the system became generic.

## Solution

### Pattern 1: Generic Extraction Fields

Replace domain-specific structured extraction with descriptive generic fields:

```python
# Before (summarize.py deep mode)
KEY QUOTES: [2-3 exact phrases from reviews/marketing, or "None found"]
TONE: [one sentence on persuasion approach, or "N/A"]

# After
KEY EVIDENCE: [2-3 direct quotes or data points that support the main claims, or "None found"]
PERSPECTIVE: [one sentence on the source's analytical stance or framing, or "N/A"]
```

**Why these names:**
- "KEY EVIDENCE" is domain-neutral — works for academic papers (data), news
  (quotes), marketing (claims), and technical docs (benchmarks).
- "PERSPECTIVE" captures how the source frames its argument without assuming
  a specific methodology. Outperforms "METHODOLOGY" because non-academic
  sources don't have methodologies. (Source: prompt template analysis,
  arxiv 2504.02052v2)

### Pattern 2: Replace Domain Language with Context-Relative Language

Seven prompt locations changed "business" to "research" or removed domain
assumptions entirely:

| Location | Before | After |
|----------|--------|-------|
| `synthesize.py:220` | "Business context is provided" | "Research context is provided" |
| `synthesize.py:225` | "Business context is provided" | "Research context is provided" |
| `synthesize.py:498-501` | "positioning, threats, opportunities, and actionable recommendations tailored to the business" | "specific details from the context to ground your recommendations in the user's situation" |
| `synthesize.py:612` | "The business context...is trusted" | "The research context...is trusted" |
| `decompose.py:111` | "relevant to the user's business" | "relevant to the user's context" |
| `context_result.py:26` | "business context" docstring | "research context" docstring |

**Key insight:** "Research context" is the right generic term because the system
IS a research agent. The context file provides background for the research, not
business intelligence specifically.

### Pattern 3: Explicit None over Hidden Defaults

```python
# Before: None silently loads a default file
DEFAULT_CONTEXT_PATH = Path("research_context.md")

def load_full_context(context_path=None):
    if context_path is None:
        context_path = DEFAULT_CONTEXT_PATH  # Hidden behavior!

# After: None means "not configured"
def load_full_context(context_path=None):
    if context_path is None:
        return ContextResult.not_configured()  # Explicit, testable
```

This gives the system four clean states:
- `loaded` — context file found and parsed
- `not_configured` — user didn't specify a context (no file loaded)
- `empty` — context file exists but has no content
- `failed` — context file couldn't be read

The old code conflated "not configured" with "use the default" — two different
intents sharing one code path.

### Pattern 4: Always Run the Relevance Gate

```python
# Before: single file = always load
if len(available) == 1:
    return available[0]  # Skips LLM check!

# After: single file still goes through relevance check
# (deleted the short-circuit entirely)
```

Cost: ~$0.0003 and ~500ms per Haiku call. The pipeline takes 20-60 seconds
total. This is negligible, and correctness matters more — a user researching
Python asyncio shouldn't get business context injected because there's only
one context file on disk.

### Pattern 5: Sanitize at Consumption, Not Write

```python
# Before (critique.py write path):
sanitized_weakness = sanitize_content(weakness)  # Sanitize at write
yaml_data["weakness"] = sanitized_weakness
# Then context.py reads it back and sanitizes again → double-encode

# After:
yaml_data["weakness"] = weakness  # Write raw
# context.py _summarize_patterns() sanitizes once at consumption boundary
```

**Why consumption boundary wins:**
1. The consumption boundary (where data enters an LLM prompt) is the security
   boundary — that's where prompt injection must be blocked.
2. Write-time sanitization creates a coupling: the writer must know what the
   reader will do, and the reader must trust the writer. If either changes,
   the contract breaks.
3. Raw data on disk is more debuggable — you see the actual content, not
   encoded entities.

### Transitional Issue: Existing YAML Critique Files

YAML critique files written before this fix contain write-time-sanitized
strings (e.g., `&amp;` instead of `&`). When `_summarize_patterns()` reads
them back, it will double-encode: `&amp; → &amp;amp;`.

**Impact:** Cosmetic only — affects critique guidance text in LLM prompts, not
user-facing output.

**Resolution:** Self-healing. The system keeps only the 10 most recent critique
files. Old files cycle out naturally as new critiques are written with raw
strings. No manual intervention needed.

**Lesson:** When changing a write-then-read sanitization boundary, consider
data already on disk. If the volume is small and self-cycling, the transitional
issue can be accepted rather than migrated.

## Key Code Changes

| File | Change | Lines |
|------|--------|-------|
| `summarize.py` | KEY QUOTES→KEY EVIDENCE, TONE→PERSPECTIVE | 99-101 |
| `synthesize.py` | "business"→"research" in 4 prompt locations | 220, 225, 498-501, 612 |
| `decompose.py` | "user's business"→"user's context" | 111 |
| `context_result.py` | Docstring generification | 26 |
| `context.py` | Remove `DEFAULT_CONTEXT_PATH`, remove single-file short-circuit, fix double-sanitization in `_summarize_patterns` | 18, 264-269, 420 |
| `critique.py` | Remove write-time sanitization | 205 |
| `agent.py` | Update `_load_context_for` docstring | 108 |
| Tests | Updated assertions across 5 test files | ~40 lines |

Net change: **-210 lines** (subtractive refactoring).

## Prevention

### When Expanding a Pipeline Beyond Its Original Domain

1. **Grep for domain language in prompts.** Search for the original domain's
   vocabulary (e.g., "business", "marketing", "competitive"). Every hit is a
   potential coupling point.

2. **Test with out-of-domain queries.** If the pipeline was built for business
   analysis, test with "Python async best practices" and verify the output
   doesn't mention business concepts.

3. **Replace domain terms with role-relative terms.** "Research context" is
   better than "business context" because it describes the data's role in the
   system, not its content domain.

### When Designing Default Behavior

4. **Explicit None over hidden defaults.** If `None` triggers a fallback,
   that's a hidden coupling. Use typed result objects (enum, dataclass) to
   make each state visible and testable.

5. **Short-circuits must preserve invariants.** If the normal path runs a
   relevance check, the fast path should too — or document clearly why it's
   safe to skip.

### When Choosing Sanitization Boundaries

6. **Sanitize at consumption, not production.** The consumer knows what
   format it needs. The producer can't predict all consumers.

7. **When changing boundary direction, audit existing data.** Stored data
   written under the old contract may not match the new contract. Calculate
   the transitional period and decide: migrate or wait it out.

## Risk Resolution

| Flagged Risk | What Happened | Lesson |
|---|---|---|
| "PERSPECTIVE" vs "METHODOLOGY" extraction quality (plan Feed-Forward) | Review found no quality issues; 8 agents approved the generic fields | Descriptive bracket text in extraction prompts is more important than the field name itself |
| Existing YAML files with write-time sanitization (fix-batched three questions) | Accepted as transitional — files cycle out within ~10 critiques | Not every data contract change needs a migration; calculate the TTL first |
| Auto-detect with adversarial LLM responses (review three questions) | Not addressed this cycle — noted for future hardening | Word-matching fallback in `auto_detect_context` is unverified at scale |

## Three Questions

1. **Hardest pattern to extract from the fixes?** The relationship between
   Pattern 2 (context-relative language) and the earlier conditional-prompt-templates
   solution. That solution gates on *whether* context exists; this one ensures the
   prompts don't assume *what kind* of context it is. They're complementary layers:
   first decide if context applies, then use neutral language so any context works.

2. **What did you consider documenting but left out, and why?** A prompt-language
   style guide ("always use 'research context' not 'business context'", "prefer
   'evidence' over 'quotes'"). Left it out because the codebase now has zero
   domain-specific prompt language — the guide would protect against regression,
   but the grep-based acceptance criterion (`grep -rn "business" research_agent/
   --include="*.py"` returns zero) is a more durable check.

3. **What might future sessions miss that this solution doesn't cover?** Context
   files themselves can contain domain-specific YAML template sections (e.g.,
   `pfe.md` defines "Buyer Psychology" as a section). The pipeline is now agnostic,
   but the *context files* still define domain-flavored output. If someone writes
   a bad context file with sections like "Competitive Threats" but uses it for
   technical research, the output will be confusing. There's no validation that
   a context file's template sections make sense for the query.

## Related Documentation

- [conditional-prompt-templates-by-context.md](../logic-errors/conditional-prompt-templates-by-context.md) — Predecessor: gates domain-specific sections on context *presence*. This solution goes further: makes prompts neutral so any context works.
- [non-idempotent-sanitization-double-encode.md](../security/non-idempotent-sanitization-double-encode.md) — Root pattern. This solution adds the write-time vs read-time boundary choice and the transitional data issue.
- [context-path-traversal-defense-and-sanitization.md](../security/context-path-traversal-defense-and-sanitization.md) — Prior cycle hardened context loading security. This cycle removed `DEFAULT_CONTEXT_PATH`, completing the explicit-context-only architecture.
- Plan: `docs/plans/2026-02-27-feat-flexible-context-system-plan.md`
- Review: `docs/reviews/flexible-context-system/REVIEW-SUMMARY.md`
