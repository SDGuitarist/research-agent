# Research Agent Entropy Audit: Applying Prompting Principles to the Codebase

## Purpose

This report maps the five entropy problems (entropy collapse, hallucination, signal-to-noise degradation, web search interference, and knowledge vacuums) to specific mechanisms in the research-agent codebase. For each finding, it identifies the root cause, the affected module, and a suggested mitigation.

---

## How the Pipeline Maps to the Entropy Principles

The research agent is a multi-stage pipeline where each stage shapes the probability distribution of the next:

```
User Query → Decompose → Search → Fetch/Cascade → Summarize → Relevance Score → Synthesize → Report
                                                                                      ↑
                                                                                   Skeptic
```

Every principle from the entropy report applies here — but the user is not the one prompting the model. **The code is.** That means the code's prompt construction, thresholds, and fallback logic are the "prompting technique" that determines output quality.

---

## Finding 1: No Vague Query Detection (Signal-to-Noise)

**Problem:** The pipeline accepts any user query and passes it directly to decomposition and search. A query like "what's trending" or "tell me about things" enters the system unchanged.

**Where:** `decompose.py` classifies queries as SIMPLE or COMPLEX but never checks if the query itself is meaningful enough to produce useful results.

**Entropy effect:** A vague query activates multiple interpretations in search results. Tavily and DuckDuckGo return scattered, topically diverse results. The summarizer then processes noise. The relevance scorer (cutoff 3/5) lets "partially relevant" sources through. The synthesizer blends everything into a report that covers many angles superficially — the exact signal-to-noise pattern from the entropy report.

**Cascade:** Vague query → noisy search → noisy summaries → permissive relevance gate → noisy synthesis. Each stage inherits and amplifies the previous stage's noise.

**Suggested mitigation:** Add a pre-decomposition query validation step. Flag queries with fewer than 3 meaningful words, or queries that are entirely generic (no proper nouns, no specific domain terms). Return a prompt asking the user to be more specific rather than searching on a bad query. This is the "state your interpretation explicitly" principle applied at the system level.

---

## Finding 2: Permissive Relevance Cutoff (Signal-to-Noise)

**Problem:** All three modes use `relevance_cutoff=3`, which maps to "Partially relevant, touches on the topic but missing key specifics." Sources that merely touch on the topic pass through to synthesis.

**Where:** `relevance.py` scoring and `modes.py` configuration.

**Entropy effect:** A score of 3 means the model is uncertain whether the source is useful. By including these borderline sources, the pipeline feeds ambiguous signal into the synthesizer. The synthesizer must then blend strong sources (score 5) with weak ones (score 3) in the same report, diluting the overall quality. This is the "web search adds a second noise source" principle — but self-inflicted.

**Compounding factor:** Relevance scoring uses Haiku (cheaper, faster model), while synthesis uses Sonnet. Haiku may miss nuance on borderline cases, letting through sources that Sonnet would have scored lower. The scoring model is less capable than the model that has to work with the scored results.

**Suggested mitigation:** Consider raising the cutoff to 4 for standard and deep modes (keep 3 for quick mode where fewer sources are available). Alternatively, pass the relevance score to the synthesizer so it can weight sources accordingly rather than treating all passing sources equally.

---

## Finding 3: No Source Diversity Enforcement (Entropy Collapse)

**Problem:** The relevance gate checks only whether enough sources pass the score threshold. It does not check whether those sources are diverse — four sources from the same domain or perspective all pass as "4+ sources = full report."

**Where:** `relevance.py` `evaluate_sources()` gate logic.

**Entropy effect:** When all passing sources share the same perspective, the synthesizer receives a low-entropy input distribution. It produces a report that sounds well-sourced (multiple citations) but represents a single viewpoint. This is entropy collapse at the pipeline level — the model is confident because all its inputs agree, but the agreement may reflect search bias rather than truth.

**Suggested mitigation:** Track source domains in the relevance gate. Require sources from at least N distinct domains (e.g., 2 for quick, 3 for standard, 4 for deep) before triggering a full report. This is the "ask for multiple perspectives" principle applied structurally.

---

## Finding 4: Chunking Loses Cross-Chunk Context (Knowledge Vacuum)

**Problem:** `summarize.py` splits sources into 4,000-character chunks (max 3 per source) and summarizes each chunk independently. The summarizer sees no inter-chunk context — it doesn't know what came before or after.

**Where:** `summarize.py` `_chunk_text()` and `_summarize_chunk()`.

**Entropy effect:** A source that builds an argument across 12,000+ characters gets split into three isolated pieces. The summarizer may:
- Miss conclusions that depend on premises in an earlier chunk
- Produce redundant summaries if the same point spans two chunks
- Drop the most important content entirely if it falls beyond the 3-chunk cap

This creates a knowledge vacuum in the synthesizer — it has fragments that look like complete information but are missing critical context. The synthesizer then fills the gaps from its training distribution, which is the hallucination mechanism described in the entropy report.

**Suggested mitigation:** Pass a brief context header to each chunk summarization call: "This is chunk N of M from [source title]. Previous chunk covered: [one-sentence summary]." This gives the model enough framing to avoid redundancy and maintain argument flow. This is the "front-load context" principle applied within the pipeline.

---

## Finding 5: Character-Level Token Budget Truncation (Knowledge Vacuum)

**Problem:** When source text exceeds the token budget, `token_budget.py` truncates at the character level — not at sentence or paragraph boundaries. A fact like "Revenue grew 15% (95% CI: 12-18%)" could be cut to "Revenue grew 15% (95% CI:" — losing the uncertainty information while keeping the point estimate.

**Where:** `token_budget.py` `truncate_to_budget()`.

**Entropy effect:** The synthesizer receives content that looks complete but has been silently truncated. It doesn't know what was lost. If statistical ranges, caveats, or qualifying statements were cut, the synthesizer works with a falsely precise input. This is the "false precision" failure mode from the entropy report — the model generates a confident report because the input data looked precise, when in reality the uncertainty information was removed by truncation.

**Suggested mitigation:** Truncate at sentence boundaries (find the last period before the character limit). If sources must be significantly shortened, re-summarize them at a shorter target length rather than cutting mid-content. Append a structured marker like `[Truncated: ~40% of source content removed]` so the synthesizer can hedge appropriately.

---

## Finding 6: Snippet Fallback Treated as Full Content (Web Search Interference)

**Problem:** When both Jina Reader and Tavily Extract fail, `cascade.py` falls back to using the search snippet (max ~500 characters from DuckDuckGo) as the source content. This snippet is then summarized, scored, and potentially included in the final report alongside sources with thousands of characters of content.

**Where:** `cascade.py` snippet fallback layer.

**Entropy effect:** A 500-character snippet lacks context, nuance, and supporting evidence. When the relevance scorer evaluates it, the snippet may score well (it contains keywords from the query) despite having almost no informational depth. When it reaches synthesis, the model must treat this thin source alongside rich ones. It either:
- Gives it equal weight (noise dilution), or
- Pattern-matches the snippet's framing and extends it from training knowledge (hallucination risk)

This is the "snippet bias" problem from the entropy report — the model reconstructs meaning from fragments using its priors.

**Suggested mitigation:** Tag snippet-sourced content with a quality tier marker that the synthesizer can see. Instruct the synthesizer to cite snippet sources only for corroboration, not as primary evidence. Consider scoring snippet sources with a penalty (e.g., max score 3 regardless of content match) to prevent them from being treated as authoritative.

---

## Finding 7: Skeptic Findings Not Enforced in Synthesis (Hallucination)

**Problem:** The skeptic module can flag a claim as `[Critical Finding]` or `[Concern]`, but the synthesis pipeline does not enforce a response. The draft report is passed to final synthesis alongside skeptic findings, but the synthesizer can ignore skeptic flags and use the original claim unchanged.

**Where:** `skeptic.py` output → `synthesize.py` `synthesize_final()` input.

**Entropy effect:** The skeptic exists specifically to catch hallucination and unsupported claims. But because its output is advisory rather than enforced, critical findings may appear in the "Adversarial Analysis" section of the report while the contradicted claim remains in the "Key Findings" section. The user sees both and must reconcile them manually. This undermines the entire verification layer.

**Suggested mitigation:** When the skeptic flags a `[Critical Finding]` related to a specific claim, require the synthesizer to either:
1. Remove the claim from the report, or
2. Explicitly mark it as disputed with the skeptic's reasoning inline

This could be implemented as a structured instruction in the final synthesis prompt: "For any claim flagged as [Critical Finding] in the skeptic analysis, you MUST either remove it or present it with an explicit uncertainty marker."

---

## Finding 8: Non-Idempotent Sanitization (Signal-to-Noise)

**Problem:** `sanitize_content()` replaces `&` with `&amp;`, `<` with `&lt;`, `>` with `&gt;`. If called twice on the same content, `&amp;` becomes `&amp;amp;`. This is a known issue — the codebase has comments warning against double-sanitization.

**Where:** `sanitize.py`, with call sites across `decompose.py`, `search.py`, `summarize.py`, `relevance.py`, `synthesize.py`, and `skeptic.py`.

**Entropy effect:** Double-sanitization corrupts data. Mathematical expressions, HTML entities, and technical content get mangled. The model then processes corrupted text, which is noise. For technical queries (research involving statistics, code, or scientific notation), this corruption removes real signal.

**Suggested mitigation:** Make sanitization idempotent — check if content is already sanitized before escaping, or use Python's `html.escape()` which handles this correctly. Alternatively, sanitize once at ingestion (when content first enters the pipeline) and pass a flag or use a wrapper type to prevent re-sanitization downstream.

---

## Finding 9: Quick Mode Single-Source Reports (Hallucination + Knowledge Vacuum)

**Problem:** Quick mode sets `min_sources_short_report=1`. A single source scoring 3/5 ("partially relevant") can trigger a report. Quick mode also disables decomposition (complex queries not split) and skeptic review (no adversarial verification).

**Where:** `modes.py` quick mode configuration.

**Entropy effect:** This is the worst-case combination from the entropy report: a single, possibly tangential source, with no verification, generating a report that looks like a researched analysis. If the source is a snippet fallback (500 chars), the synthesizer builds the entire report from one thin fragment plus its training distribution. This maximizes hallucination risk — the model fills the vacuum with plausible-sounding content derived from adjacent knowledge.

**Suggested mitigation:** Raise `min_sources_short_report` to 2 for quick mode. Add a visible confidence indicator to quick-mode reports: "Based on [N] sources — confidence: low/medium/high." This gives the user the uncertainty signal that the pipeline can't otherwise provide.

---

## Finding 10: Refinement Loop Based on Noise (Web Search Interference)

**Problem:** If the first search pass returns low-quality results, `search.py` `refine_query()` uses summaries from those results to generate a refined query. Bad first-pass results produce a refined query that's shaped by noise.

**Where:** `search.py` `refine_query()` and `_research_with_refinement()` in `agent.py`.

**Entropy effect:** This is the "retrieval quality bottleneck" from the entropy report, compounded by a feedback loop. The refinement prompt feeds up to 10 summaries from the first pass to Claude and asks for a better query. If those 10 summaries are tangential or noisy, the refined query inherits their framing. The second pass searches for something shaped by the first pass's noise rather than by the user's original intent.

**Suggested mitigation:** Before refining, check the score distribution of first-pass results. If all sources scored 2 or below, skip refinement and instead try a simpler reformulation of the original query (e.g., extract key noun phrases). Only use summary-based refinement when the first pass had at least some relevant results (score 4+) to anchor the refinement.

---

## Risk Summary

| # | Finding | Entropy Problem | Severity | Effort |
|---|---------|----------------|----------|--------|
| 1 | No vague query detection | Signal-to-noise | High | Low |
| 2 | Permissive relevance cutoff (3/5) | Signal-to-noise | Medium-High | Low |
| 3 | No source diversity enforcement | Entropy collapse | Medium | Medium |
| 4 | Chunking loses cross-chunk context | Knowledge vacuum | Medium | Medium |
| 5 | Character-level truncation | Knowledge vacuum | Medium | Medium |
| 6 | Snippet fallback = full content | Web search interference | Medium-High | Low |
| 7 | Skeptic findings not enforced | Hallucination | High | Medium |
| 8 | Non-idempotent sanitization | Signal-to-noise | Medium | Low |
| 9 | Quick mode single-source reports | Hallucination + vacuum | Medium-High | Low |
| 10 | Refinement loop amplifies noise | Web search interference | Medium | Medium |

---

## Recommended Fix Order

Address these in dependency order — some fixes amplify the impact of others:

| Order | Finding | Why This Order |
|-------|---------|---------------|
| 1 | #1 — Vague query detection | Prevents noise from entering the pipeline at all. Reduces load on every downstream stage. |
| 2 | #8 — Idempotent sanitization | Data corruption affects every stage. Fix the foundation first. |
| 3 | #2 — Raise relevance cutoff | Reduces noise reaching synthesis. Makes #3 and #7 less urgent. |
| 4 | #6 — Snippet quality tier | Prevents thin sources from being treated as authoritative. |
| 5 | #9 — Quick mode minimum sources | Prevents single-source reports. Quick win. |
| 6 | #7 — Enforce skeptic findings | Closes the hallucination verification gap. |
| 7 | #10 — Score-aware refinement | Prevents noise feedback loops. |
| 8 | #3 — Source diversity gate | Prevents false confidence from homogeneous sources. |
| 9 | #4 — Cross-chunk context | Improves summarization quality for long documents. |
| 10 | #5 — Sentence-boundary truncation | Prevents false precision from mid-fact cuts. |

---

## What the Codebase Already Does Well

The analysis is not all problems. Several design decisions directly address entropy principles:

- **Three-layer prompt injection defense** — Sanitization + XML boundaries + system prompt isolation. This prevents retrieved web content from hijacking model behavior.
- **Structured summarization format** — FACTS / KEY EVIDENCE / PERSPECTIVE forces the summarizer to separate claims from interpretation, reducing hallucination.
- **Skeptic module exists** — Three independent adversarial lenses (evidence, timing, framing) is a strong design. The issue is enforcement, not detection.
- **Mode-specific model routing** — Using Haiku for planning/scoring and Sonnet for synthesis is cost-efficient and places the stronger model where entropy management matters most.
- **Relevance scoring with explanations** — The scorer is asked to explain its score, not just output a number. This reduces arbitrary scoring.
- **Token budget priority system** — Instructions are never cut, sources are cut last. The priority order is correct even if the truncation method needs improvement.
- **Query refinement with overlap validation** — Refined queries must be 20%+ different from the original, preventing circular refinement.

---

## Key Takeaway

The research agent is a system that prompts AI models on behalf of the user. Every entropy principle that applies to human-to-AI prompting applies here — but the stakes are higher because the prompting happens in code, at scale, with no human review of intermediate steps.

The highest-impact improvements are at the pipeline boundaries: **input validation** (don't search on bad queries) and **output enforcement** (don't ignore skeptic findings). These are low-effort, high-leverage changes that address the two most dangerous failure modes: noise entering the system and hallucination escaping it.
