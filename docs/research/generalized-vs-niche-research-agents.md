# Generalized vs. Niche-Focused Research Agents

**Date:** 2026-02-15
**Status:** Consideration
**Context:** Evaluating architectural direction for the research agent

---

## Generalized Deep Research Agent

**Pros:**
- Handles any topic — one tool for everything
- Larger potential user base
- Learns patterns that transfer across domains
- More resilient to niche markets dying out

**Cons:**
- Jack of all trades, master of none — can't go as deep on specialized topics
- Harder to tune prompts (what works for medical research may hurt financial analysis)
- Source selection is generic — doesn't know which sources are authoritative per domain
- Quality ceiling is lower for expert users who need domain depth

## Niche-Focused Research Agent

**Pros:**
- Domain-specific source lists, scoring heuristics, and output formats
- Prompts tuned for the vocabulary and reasoning patterns of that field
- Can encode domain knowledge (e.g., "for hospitality, always check STR reports")
- Higher trust from users — feels like it "gets" their work
- Easier to validate quality (narrower scope = clearer benchmarks)

**Cons:**
- Smaller addressable market
- Falls apart outside its lane
- Risk of over-fitting to one customer's workflow
- More effort to expand into adjacent domains later

## Where Our Agent Falls

The research agent sits in an **interesting middle ground** — architecturally general but operationally niche.

### General elements
- The pipeline (decompose → search → fetch → cascade → summarize → synthesize) works for any topic
- Tavily + DuckDuckGo search is domain-agnostic
- The cascade fallback (Jina → Tavily Extract → snippet) handles any URL
- Mode system (quick/standard/deep) is universally useful

### Niche elements
- `research_context.md` injects Pacific Flow Entertainment's business context into decomposition and synthesis
- The relevance scoring and synthesis prompts are shaped by what matters to our use case
- The skeptic module's verification agents (evidence, timing, framing) reflect a specific editorial standard

### Assessment
The agent is a **general engine with a niche configuration layer**. The pipeline doesn't care what it's researching, but the context file and prompt tuning make it perform best for the Pacific Flow domain.

## Possible Directions

### Push More General
- Make `research_context.md` a swappable profile system (one per client/domain)
- Same agent serves different niches through configuration alone

### Push More Niche
- Add domain-specific source lists
- Custom scoring weights per industry
- Output templates tailored to specific deliverables (e.g., competitor briefs vs. market reports)

### Key Principle
Keep the engine general, push specialization into configuration and prompts. Avoid rebuilding the pipeline for each niche.
