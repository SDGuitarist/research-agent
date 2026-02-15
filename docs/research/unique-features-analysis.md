# Unique Features Analysis — Pacific Flow Research Agent

**Date**: 2026-02-15
**Method**: Codebase analysis cross-referenced against research-agent-features-2025-2026.md, research-agent-integrations.md, and cycle-17 architecture analysis

---

## 1. Three-Lens Adversarial Skeptic System

**No other open-source research agent has this.** `skeptic.py` runs three distinct adversarial reviewers against the draft before final synthesis:

| Lens | What It Checks |
|---|---|
| **Evidence Alignment** | Tags every claim as SUPPORTED / INFERRED / UNSUPPORTED against cited sources |
| **Timing & Stakes** | Evaluates cost-of-waiting vs cost-of-acting; catches "strategic patience" bias |
| **Break the Trolley** | Challenges the analytical *frame itself* — whether the analysis solves the right problem |

In deep mode, these chain sequentially — the frame agent sees evidence + timing findings before running, building on prior analysis. In standard mode, all three run in a single combined call.

**Why it's unique**: GPT-Researcher has a Reviewer + Reviser, but those operate *within* the existing frame. STORM uses multi-perspective questioning but during *generation*, not as post-hoc verification. FutureHouse Falcon detects source conflicts, but no agent questions whether the analytical frame should be rejected entirely. The "Break the Trolley" lens — checking if sophistication is disguising inaction as "strategic patience" — is architecturally novel.

---

## 2. Context-Isolated Two-Pass Synthesis

The pipeline deliberately generates the **factual draft (sections 1-8) without business context**, then adds business context only for the **analytical sections (9-13)**. This prevents "context bleeding" — where knowing the user's business biases the factual reporting.

```
synthesize_draft()  → sections 1-8, NO business context (factual)
skeptic pass        → adversarial review with business context
synthesize_final()  → sections 9-13, WITH business context + skeptic findings (analytical)
```

**Why it's unique**: GPT-Researcher, STORM, Perplexity, and all commercial deep research products feed context uniformly throughout synthesis. No other agent architecturally separates fact-gathering from business-contextualized analysis. This is a deliberate design choice documented in cycle-17-01 codebase analysis.

---

## 3. Three-Layer Cascade Recovery

`cascade.py` ensures no source is ever fully lost:

| Layer | Service | Cost | Trigger |
|---|---|---|---|
| 1 | Jina Reader | Free | All failed URLs |
| 2 | Tavily Extract | 1 credit / 5 URLs | High-value domains only (yelp, instagram, weddingwire, etc.) |
| 3 | Snippet fallback | Free | Remaining failures — uses search snippet as thin content |

**Why it's unique**: GPT-Researcher and STORM retry or skip failed fetches. They don't cascade across extraction services. The domain-aware gating on Layer 2 — only spending Tavily Extract credits on domains worth the cost — is a cost-optimization detail no other agent implements.

---

## 4. LLM-Powered Relevance Gate with Source-Level Aggregation

`relevance.py` scores each source chunk individually via Claude, then **aggregates to source-level using max score across chunks**, and gates the pipeline into three decisions:

| Decision | Meaning |
|---|---|
| `full_report` | Enough relevant sources for comprehensive analysis |
| `short_report` | Below full threshold but above minimum — generates report with disclaimer |
| `insufficient_data` | Too few relevant sources — generates explanation + alternative query suggestions |

The "insufficient data" path is itself a thoughtful output: Claude explains *why* nothing relevant was found and suggests alternative queries and platforms.

**Why it's unique**: Most agents use embedding similarity or keyword matching for relevance. This agent uses an LLM call per chunk with adaptive batched rate-limit backoff. The three-way decision gate (not just pass/fail) and the source-level aggregation (Cycle 15: "score the unit you decide on") are distinct from any documented research agent architecture.

---

## 5. Three-Layer Prompt Injection Defense

Defense is layered across the entire pipeline:

| Layer | Mechanism | Location |
|---|---|---|
| **Content sanitization** | Escapes XML delimiters (`<` → `&lt;`) in all untrusted content | `sanitize.py` — single source of truth |
| **XML boundaries** | External content wrapped in `<sources>`, `<source_summary>`, `<draft_analysis>` tags | All synthesis/scoring prompts |
| **System prompt guardrails** | Every LLM call warns to ignore instructions found in source content | `synthesize.py`, `relevance.py`, `skeptic.py` |

Research (MDPI study, arXiv:2511.15759) shows multi-layered defense reduces prompt injection attack success from 73.2% to 8.7%. Most research agents either do nothing or rely on a single layer. OpenAI has stated deterministic defense is impossible — layering is the only viable strategy.

---

## 6. SSRF Protection with DNS Rebinding Defense

`fetch.py` goes beyond basic URL validation:

1. Blocks non-HTTP(S) schemes (`file://`, `ftp://`, etc.)
2. Blocks known localhost/loopback hostnames
3. **Async DNS resolution** — resolves the hostname and validates **every resolved IP** against private, loopback, link-local, multicast, and reserved ranges

Step 3 prevents DNS rebinding attacks where a hostname initially resolves to a public IP but later resolves to `127.0.0.1`. No other open-source research agent implements fetch-layer DNS rebinding defense.

---

## 7. Deep Mode Two-Pass Search with Summary-Informed Refinement

| Mode | Pass 2 Refinement Source |
|---|---|
| Standard | Search **snippets** (fast, shallow) |
| Deep | Full **summaries** from pass 1 (slow, informed) |

In deep mode, the agent completes the entire fetch → extract → cascade → summarize pipeline for pass 1 before formulating its refined pass-2 query. This means the refined query is informed by fully processed content, not just search result previews.

**Why it's unique**: GPT-Researcher does recursive subtopic exploration. STORM does multi-perspective conversation. Neither does full-content-informed query refinement between search passes. This is architecturally more expensive but produces significantly better second-pass searches.

---

## 8. Sub-Query Divergence Validation

`decompose.py` enforces that generated sub-queries aren't just rearrangements of the original query:

- **Max overlap check** (`MAX_OVERLAP_WITH_ORIGINAL = 0.8`) — rejects sub-queries that share 80%+ meaningful words with the original
- **Near-duplicate detection** — rejects sub-queries that overlap 70%+ with each other
- **Prompt-level enforcement** — BAD/GOOD examples teach the LLM to generate genuinely new angles, not restatements
- **Word count bounds** — rejects sub-queries under 2 or over 10 words

**Why it's unique**: Cycle 13 revealed that most LLMs default to restating the query with different word order, wasting API calls on redundant searches. No other documented research agent validates sub-query divergence at this level.

---

## Features That Are Well-Executed But Not Unique

| Feature | Status |
|---|---|
| Pipeline shape (decompose → search → fetch → extract → summarize → synthesize) | Dominant pattern — GPT-Researcher, STORM, commercial products |
| Tavily + DuckDuckGo fallback | Common dual-search pattern |
| Frozen dataclass mode configs | Good engineering, not novel |
| CLI-first interface | Aligned with GPT-Researcher |
| User-Agent rotation | Standard scraping practice |
| Streaming synthesis output | Universal across all LLM-based agents |

---

## Summary

The strongest differentiators cluster in two areas:

**Adversarial quality control** — The skeptic system (especially "Break the Trolley"), context-isolated synthesis, and three-way relevance gating form a verification layer that no other research agent matches. Most agents generate and ship; this one generates, challenges, and then ships.

**Defense in depth** — Three-layer prompt injection defense, SSRF protection with DNS rebinding prevention, and content sanitization as a single source of truth. These are areas where most research agents — even well-funded commercial ones — cut corners.
