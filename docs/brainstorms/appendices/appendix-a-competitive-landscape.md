# Appendix A: Competitive Landscape — Autonomous Research Agents (April 2026)

**Source:** competitive-map agent, 2026-04-21

## Competitors

### Google Deep Research Max
**Moat:** Full Google Search index, native visualization, Gemini 3.1 Pro, multimodal input, collaborative planning, ecosystem lock-in (Workspace).
**Gaps:** No adversarial self-verification, no prompt injection defense discussion, no cross-session memory, no source quality tiering, no domain-level source control.
**Adopt:** Collaborative planning (`--plan-review` flag). Consider visualization (already planned C37).

### Perplexity
**Moat:** Best citation transparency (78% claim-to-source rate, Columbia Tow Center study). Speed (358ms median). Multi-model routing. API access (Sonar). Free tier.
**Gaps:** No adversarial verification, no cross-session memory, no context isolation, no domain-level source control, text-only output.
**Adopt:** Study their citation UX for C37 visualization. Consider multi-model routing long-term.

### OpenAI Deep Research
**Moat:** Deepest reasoning (o3/o4-mini). Multimodal analysis. Dynamic pivoting. Agents SDK. Code execution during research.
**Gaps:** Expensive ($200/mo Pro). No adversarial self-check. No cross-session state. Slow (5-30 min). Closed architecture.
**Adopt:** Code execution during research (consider for H3). Study Agents SDK handoff pattern for C39 swarm.

### Exa
**Moat:** Neural/semantic search ("next-link prediction"). Research API (94.9% SimpleQA). Sub-200ms instant search. Structured output.
**Gaps:** Smaller index. Higher cost. No report generation (search/retrieval only).
**Adopt:** Add as third search provider (semantic queries where Tavily's keyword results are weak).

### Tavily
**Moat:** Built for AI agents. Research endpoint (managed multi-step workflow). GPT-Researcher connection. Competitive pricing.
**Gaps:** Research endpoint competes with you. No adversarial verification. API dependency risk.
**Watch:** Their research endpoint evolution. If it gets good enough with verification, consume it as a building block.

### Open-Source Agents
- **GPT-Researcher** (~20K+ stars): Plan-and-Solve + RAG, outperforms Perplexity/OpenAI on citation quality (DeepResearchGym). Study for C39 swarm.
- **STORM** (Stanford): Multi-perspective questioning during generation. Philosophically aligned with skeptic system. Study for perspective-guided generation.
- **LangChain Open Deep Research**: Simple, configurable reference architecture. #6 on Deep Research Bench.
- **DeepResearchAgent** (SkyworkAI): Hierarchical multi-agent with MCP. Up to 400 tool calls.

## Capabilities No Competitor Has (Your Pioneering Opportunities)

| Capability | Why No One Has It |
|---|---|
| Active counter-search | Requires adversarial design intent, commercially unappealing |
| Per-claim epistemic provenance | Requires structured evidence tracking through entire pipeline |
| Context-isolated synthesis | Non-obvious design choice (slower but less biased) |
| Cross-session research memory with staleness | Requires persistent state infrastructure most avoid |
| Frame-questioning verification ("Break the Trolley") | Philosophically unusual adversarial approach |

## Biggest Risk

**Search index dependency.** Google queries the full index. You depend on Tavily + DDG. Best adversarial verification can't find disconfirming evidence the search API never returns.

**Mitigation:** Exa for semantic search (C38), "search coverage confidence" dimension in C33.

## Does the Epistemic Rigor Moat Hold?

**Yes, with caveats:**
1. Commercial incentive misalignment protects you (confident reports drive engagement)
2. Architectural depth is hard to copy (verification woven through pipeline, not bolted on)
3. Epistemic calibration study provides empirical backing
4. Columbia Tow Center found ~37%+ citation error rates across ALL commercial systems

**Caveats:** Epistemic rigor only matters to users who care. The moat is behavioral, not structural. Search coverage gap undermines rigor claim.
