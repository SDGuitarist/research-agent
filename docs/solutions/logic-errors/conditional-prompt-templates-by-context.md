---
title: Conditional Prompt Templates Based on Context Availability
date: 2026-02-26
category: logic-errors
tags: [synthesis, prompt-engineering, conditional-templates, business-context]
module: research_agent
symptoms: [irrelevant-business-sections-in-technical-reports, forced-buyer-psychology-for-non-business-queries]
severity: medium
summary: Synthesis prompts hardcoded business-intelligence sections for all queries. Technical queries got forced into irrelevant categories (Buyer Psychology, Service Portfolio). Fix selects template based on whether business context is configured.
---

# Conditional Prompt Templates Based on Context Availability

**Cycle 20** | 2026-02-26

## Problem

`synthesize_draft()` and `synthesize_final()` hardcoded business-intelligence report sections for ALL queries:

- Company Overview, Service Portfolio, Marketing Positioning
- Messaging Theme Analysis, Buyer Psychology
- Competitive Implications, Positioning Advice

A query like "how does Python asyncio work" would get forced into these categories. The LLM would either hallucinate business content or produce empty sections, making reports confusing and unreliable for non-business research.

## Root Cause

The prompt templates were written when the agent only served one use case (competitive intelligence for Pacific Flow Entertainment). When the agent expanded to general research, the templates weren't updated — they assumed business context always existed.

## Solution

Branch on `has_business_context` to select the appropriate template at two points:

### Draft synthesis (`synthesize_draft`)

Added `has_business_context: bool = False` parameter. Two template paths:

| Context | Sections |
|---------|----------|
| **With business context** | 1. Executive Summary, 2. Company Overview, 3. Service Portfolio, 4. Marketing Positioning, 5. Messaging Theme Analysis, 6. Buyer Psychology, 7. Content & Marketing Tactics, 8. Business Model Analysis |
| **Without business context** | 1. Executive Summary, 2. Key Findings, 3. Technical Details, 4. Practical Recommendations |

### Final synthesis (`synthesize_final`)

Branches on whether `business_context` is truthy (already a parameter):

| Context | Sections |
|---------|----------|
| **With business context** | Competitive Implications, Positioning Advice, [Adversarial Analysis if skeptic], Limitations & Gaps, Sources |
| **Without business context** | [Adversarial Analysis if skeptic], Limitations & Gaps, Sources |

### Caller change (`agent.py`)

```python
# agent.py passes the flag based on context loading result
draft = synthesize_draft(
    client, query, surviving,
    model=model,
    has_business_context=bool(synthesis_context),
)
```

The `synthesis_context` variable already existed from the context loading pipeline — just needed to thread it through as a boolean.

## Key Pattern

**When an LLM prompt contains domain-specific structure (section headings, categories, terminology), gate it on whether the domain context is actually present.** Don't assume the context that existed when the prompt was written will always exist.

This is a specific case of a general rule: **prompt templates should be parameterized by their assumptions, not just their inputs.** The draft template assumed "this is a business query" — that assumption should have been a parameter from the start.

## Prevention

1. **Audit prompts when expanding use cases.** When a tool grows beyond its original domain, search for domain-specific language baked into prompts. Section headings like "Buyer Psychology" are the most visible symptom.

2. **Test with queries outside the original domain.** The bug was invisible when only running business queries. A single test with a technical query would have caught it.

3. **Make assumptions explicit parameters.** If a function's behavior depends on context being present, accept that as a parameter rather than assuming it. `has_business_context: bool = False` is one line that prevents the entire class of bug.

## Risk Resolution

- **Flagged:** E2E testing of `/research:queue` and `/research:digest` skills revealed business sections in technical reports
- **What happened:** Draft and final synthesis both had hardcoded business templates — two code paths to fix
- **Lesson:** When fixing conditional behavior in a multi-stage pipeline, check ALL stages. The same assumption often leaks into multiple places.

## Three Questions

1. **Hardest pattern to extract from the fixes?** Deciding whether this is a "logic error" or "architecture" category. It's both — the logic error (wrong sections) stems from an architectural assumption (single-domain prompts). Filed under logic-errors because the symptom is wrong output, not a structural problem.

2. **What did you consider documenting but left out, and why?** The specific section numbering scheme (why generic uses 1-4 and business uses 1-8). Left out because it's an implementation detail that could change — the pattern (branch on context) is what matters.

3. **What might future sessions miss that this solution doesn't cover?** Other prompts in the codebase that assume business context. `decompose.py` and `relevance.py` may also have business-flavored language that doesn't apply to generic queries. No audit was done beyond `synthesize.py`.

## Related Documentation

- [Domain-Agnostic Pipeline Design](../architecture/domain-agnostic-pipeline-design.md) —
  Cycle 22 completed the work this solution started: all "business" language in prompts
  was replaced with generic "research" language, and extraction fields were generalized.
  This solution gates on context *presence*; that one ensures neutral language for any context.
- [`docs/solutions/logic-errors/adversarial-verification-pipeline.md`](adversarial-verification-pipeline.md) — Cycle 16: the draft→skeptic→final pipeline this fix modifies
- `research_agent/synthesize.py` — Both template paths
- `research_agent/context.py` — Context loading (no longer called "business context")
