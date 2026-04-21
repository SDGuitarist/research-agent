# 10 Steps Ahead of Deep Research Max — Strategic Brief

**Date:** 2026-04-21
**Cycle:** TBD (merges with C29-31 roadmap — see Merge Analysis)
**Status:** Brainstorm — positioning agreed, ready for planning

---

## Prior Phase Risk

No prior brainstorm — this is a new strategic initiative. The previous phase was Cycle 29H (compound), whose "Least confident about" was: *ANTHROPIC_ERRORS is defined but only consumed in the synthesis context manager. The remaining 10+ inline exception tuples still exist.* This is a mechanical cleanup item that doesn't affect this initiative.

---

## Part 1: Where You Are Now

### Current Capabilities (31 modules, 1040 tests, v0.18.0)

| Layer | Module(s) | What It Does | Unique Advantage |
|-------|-----------|-------------|------------------|
| **Input** | `query_validation.py`, `decompose.py` | Vague query rejection, SIMPLE/COMPLEX classification, sub-query generation | Vague detection rejects noise before any API spend |
| **Search** | `search.py` | Tavily (primary) + DuckDuckGo (fallback), query refinement, blocked-domain filtering | Two-source fallback, context-aware domain blocking |
| **Fetch** | `fetch.py` | Async HTTP with SSRF protection, UA rotation | Dual SSRF validation (input + post-redirect) |
| **Recovery** | `cascade.py` | Three-layer fallback: Jina Reader → Tavily Extract → snippet | Graceful degradation with source-tier tagging |
| **Extract** | `extract.py` | trafilatura + readability-lxml, content extraction | Source tier tracking (full vs snippet) |
| **Sanitize** | `sanitize.py` | Three-layer prompt injection defense (sanitize + XML + system prompt) | Idempotent, shared across all modules |
| **Summarize** | `summarize.py` | Batched chunk summarization with Claude | Per-task temperature control (0.5) |
| **Relevance** | `relevance.py` | Source scoring (1-5), quality gate (full/short/insufficient), snippet score cap | Mode-specific cutoffs (3 quick, 4 standard/deep) |
| **Skeptic** | `skeptic.py` | Adversarial verification: evidence, timing, strategic frame lenses | Three concurrent async agents reviewing every draft |
| **Synthesis** | `synthesize.py` | Report generation with mode-specific instructions, tone presets, context-aware templates | Token budget allocation, tone presets, context injection |
| **Iteration** | `iterate.py`, `coverage.py` | Post-report refinement queries, follow-up generation, coverage gap identification | Self-improving loop within a single run |
| **Critique** | `critique.py` | Post-run quality evaluation with structured YAML output | Persistent critique history across runs |
| **Gap Schema** | `schema.py`, `state.py`, `staleness.py` | YAML-based gap tracking, state transitions, staleness detection, batch selection | Cross-session research memory — knows what's stale |
| **Context** | `context.py`, `context_result.py` | Research contexts with blocked domains, synthesis tone, gap schemas, auto-detection | Domain-specific research profiles |
| **Modes** | `modes.py` | Frozen dataclass configs (quick/standard/deep) with per-task temperatures | 39 tunable parameters per mode |
| **MCP** | `mcp_server.py` | FastMCP server exposing research as tools | AI-to-AI research capability |
| **Security** | `fetch.py`, `sanitize.py` | SSRF protection, prompt injection defense, content sanitization | Defense-in-depth at every layer |
| **Storage** | `report_store.py`, `safe_io.py` | Atomic file writes, report listing/retrieval | Crash-safe persistence |
| **Budget** | `token_budget.py` | Token counting, priority-based budget pruning | Prevents context overflow |
| **API** | `__init__.py` | Public sync/async API, structured results | Embeddable in any Python project |

### What Deep Research Max Ships (April 2026)

| Capability | Their Implementation | Your Equivalent |
|------------|---------------------|-----------------|
| Web search | Google Search index | Tavily + DuckDuckGo fallback |
| MCP for proprietary data | Arbitrary tool definitions | MCP server (exposes *your* tools, doesn't consume external MCP) |
| Native charts/infographics | Inline HTML or "Nano Banana" visualization | **None** — text-only reports |
| Collaborative planning | User reviews research plan before execution | Decomposition is automatic, no user review step |
| Multimodal input | PDFs, CSVs, images, audio, video as research context | **None** — text-only input |
| Real-time streaming | Intermediate reasoning steps streamed live | Progress bar + logging only |
| Extended test-time compute | Iterative reason/search/refine loops (Max tier) | Single iteration loop (refine → append) |
| Two tiers (speed vs depth) | Deep Research vs Deep Research Max | quick / standard / deep (three tiers) |
| File uploads + File Search | Connected file stores | Context files (YAML templates only) |
| Code execution | Runs code during research | **None** |

### What You Have That They Don't Mention

| Your Advantage | Why It Matters |
|----------------|---------------|
| Three-layer prompt injection defense | Google doesn't discuss adversarial resilience at all |
| Skeptic adversarial verification (3 lenses) | Their agent has no adversarial self-check |
| Gap schema with staleness tracking | They don't track what's been researched before or when it expires |
| Evidence-tier labeling (C29 roadmap) | They don't distinguish documented facts from inferences |
| Query vagueness detection | They don't mention input validation |
| Per-task temperature tuning (backed by epistemic study) | Their temperature is likely one-size-fits-all |
| Self-critique with structured YAML history | Their agent doesn't learn from its own mistakes |
| Blocked-domain filtering per context | No domain-level source control mentioned |
| Source-tier tagging (full vs snippet) | They don't distinguish source quality tiers |
| Atomic file writes, crash-safe persistence | Infrastructure reliability |

---

## Part 2: The Existing Roadmap (C29-31)

### What's Left

| Cycle | Theme | Items | Lines | Sessions |
|-------|-------|-------|-------|----------|
| **29** | Verification & Synthesis Integrity | Skeptic enforcement, score-aware refinement, evidence-tier labeling | ~170 | 4 |
| **30** | Summarization & Context Preservation | Source diversity gate, cross-chunk context, sentence truncation, pre-summary abstention | ~180 | 4 |
| **31** | Research Distinctiveness | Novelty-biased decomposition, MCP tools #123 | ~120 | 3 |
| **Total** | | **9 items** | **~470 lines** | **11 sessions** |

### Roadmap Philosophy

The roadmap follows a strict dependency order derived from the entropy audit and epistemic calibration study:

```
Clean input (C27 ✅) → Filter noise (C28 ✅) → Verify claims (C29) → Preserve signal (C30) → Add distinctiveness (C31)
```

Each cycle makes the next one more effective. This is the "upstream before downstream" principle.

---

## Part 3: The "10 Steps Ahead" Proposal

| # | Concept | Overlap with Roadmap | New Ground |
|---|---------|---------------------|------------|
| 1 | Multi-agent research swarm | None | Parallel specialist agents that debate |
| 2 | Structured evidence graph | C29 evidence-tier labeling is a seed | Claims → evidence → confidence as data |
| 3 | Adversarial counter-search | C29 skeptic enforcement is a seed | Active search for disconfirming evidence |
| 4 | Adaptive mid-flight re-planning | C31 score-aware refinement touches this | Autonomous strategy shifts during research |
| 5 | Cross-temporal analysis | Gap schema staleness is a seed | Track information drift over time |
| 6 | Epistemic confidence scoring | C29 evidence-tier labeling directly | User-facing confidence per claim |
| 7 | Research memory that compounds | Gap schema + critique history are seeds | Persistent knowledge graph across queries |
| 8 | Native visualization generation | None | Charts, timelines, relationship maps |
| 9 | Multi-source data fusion + conflict resolution | None (MCP is outbound only today) | Inbound MCP + web + local with conflict handling |
| 10 | Streaming reasoning trace | None | Real-time + persistent reasoning visibility |

---

## Part 4: Merge Analysis

### Verdict: MERGE — the roadmap is the foundation, the vision is the ceiling

The existing C29-31 roadmap and the "10 steps ahead" proposal are **complementary, not competing**. Here's why:

**The roadmap items are prerequisites.** You can't build a multi-agent swarm on a pipeline that doesn't enforce skeptic findings (#7) or properly tier evidence. You can't do cross-temporal analysis without staleness tracking that actually works. The roadmap fixes the plumbing; the vision builds the house.

**Specific merge points:**

| Roadmap Item | Merges Into Vision Item | How |
|-------------|------------------------|-----|
| C29: Skeptic enforcement | → #3 Adversarial counter-search | Enforcement is step 1. Counter-search extends it to actively seeking disconfirmation. |
| C29: Evidence-tier labeling | → #6 Epistemic confidence scoring | Tier labels become the foundation for per-claim confidence. |
| C29: Score-aware refinement | → #4 Adaptive re-planning | Score-aware refinement is a narrow case of adaptive planning. |
| C30: Source diversity gate | → #1 Multi-agent swarm | Diversity enforcement is a simple gate. Swarm agents inherently diversify. |
| C30: Cross-chunk context | → #2 Evidence graph | Cross-chunk context preserves relationships. Evidence graph makes them explicit. |
| C30: Pre-summary abstention | → #6 Epistemic confidence | Abstention on uncorroborated claims feeds confidence scoring. |
| C31: Novelty decomposition | → #1 Swarm (contrarian agent) | Novelty-biased queries are what a contrarian agent does naturally. |
| C31: MCP tools #123 | → #9 Multi-source data fusion | MCP tools are the interface; fusion is the logic. |

### Existing brainstorms that feed into this

| Brainstorm | Status | Merges Into |
|-----------|--------|------------|
| Self-Enhancing Agent (2026-02-20) | Brainstorm complete, partially implemented (critique.py) | → #7 Research memory that compounds |
| Background Research Agents (2026-02-25) | Brainstorm complete, not implemented | → #1 Multi-agent swarm (execution model for parallel research) |

---

## Part 5: Recommended Path — Three Horizons

### Horizon 1: Complete the Foundation (C29-31, ~11 sessions)

**What:** Finish the entropy roadmap as planned.
**Why:** These are small, validated, dependency-ordered fixes. Every "10 steps ahead" feature becomes easier with these in place. Skipping them means building on a leaky pipeline.
**Risk of skipping:** Evidence-tier labeling doesn't exist yet. Skeptic findings aren't enforced yet. Building a swarm on top of non-enforced verification is theatre.

**Modifications for the new vision:**
- C29: When implementing evidence-tier labeling, design the data model to be extensible to per-claim confidence scores (don't just use inline text markers — output structured data too)
- C31: When implementing MCP tools, also add **inbound** MCP consumption (not just outbound tools) — this is the #9 fusion foundation
- C31: Expand novelty decomposition to be the seed for the contrarian agent role

### Horizon 2: The Structural Leap (C32-35, ~20-25 sessions)

**What:** The unique capabilities that make this agent categorically different from Deep Research Max.

| Cycle | Feature | Why This Order |
|-------|---------|----------------|
| **32** | **Adversarial counter-search** — after draft, search for evidence against each major claim | Extends C29 skeptic enforcement. Low-effort, high-impact. Google doesn't do this. |
| **33** | **Epistemic confidence scoring** — every claim gets a confidence level (documented/inferred/speculative) with evidence type, output as structured data | Extends C29 evidence tiers. Makes reports auditable. Feeds into evidence graph. |
| **34** | **Adaptive mid-flight re-planning** — agent evaluates search results after each pass and adjusts strategy (new sub-queries, abandon dead ends, shift focus) | Extends C29 score-aware refinement from binary to continuous. Makes deep mode significantly smarter. |
| **35** | **Research memory that compounds** — persistent knowledge graph from critique history + gap schema + evidence graph; queried at the start of every new run | Extends gap schema + self-enhancing agent brainstorm. The agent gets smarter over time. |

**Why these four first:**
- They're all **epistemic** — they make the agent's thinking better, not just its output prettier
- They build on C29-31 directly (clear dependency chain)
- Google can't easily copy them because they require adversarial design, not just bigger models
- They're the moat: bigger models don't solve "actively try to disprove yourself"

### Horizon 3: The Experience Layer (C36-39, ~15-20 sessions)

**What:** The capabilities that make the output beautiful and the agent accessible.

| Cycle | Feature | Why This Order |
|-------|---------|----------------|
| **36** | **Streaming reasoning trace** — real-time visibility into agent thinking, stored as persistent log | Parity with Google. Low-risk. Makes the agent feel alive. |
| **37** | **Native visualization** — charts, timelines, relationship maps generated from structured evidence data | Requires evidence graph from H2. Now visualizations show real data, not cosmetic charts. |
| **38** | **Multi-source data fusion** — inbound MCP + web + local files, with conflict resolution protocol | Requires C31 MCP foundation + H2 confidence scoring to resolve conflicts. |
| **39** | **Multi-agent research swarm** — parallel specialist agents (domain, contrarian, verifier, editor) | The capstone. Requires H2 epistemic infrastructure so each agent role is meaningful. |

**Why these are last:**
- Streaming and visualization are presentation — they make good research *look* good, but don't make research *better*
- Fusion and swarm are architecturally complex and benefit most from all prior infrastructure
- The swarm specifically needs: adversarial counter-search (contrarian role), confidence scoring (verifier role), adaptive planning (coordinator role), and research memory (shared context)

---

## Part 6: What This Gives You Over Deep Research Max

| Dimension | Deep Research Max | Your Agent (After H1-H3) |
|-----------|------------------|--------------------------|
| **Epistemic integrity** | Unverified — no adversarial self-check | Triple-verified: skeptic → counter-search → confidence scoring |
| **Learning** | Stateless — every run starts from zero | Compounds — knowledge graph grows with every query |
| **Transparency** | Streams thinking but doesn't persist or structure it | Persistent reasoning trace + per-claim confidence levels |
| **Source quality** | Unstated | Five-layer gate: vague detection → relevance scoring → source tiers → diversity gate → skeptic |
| **Conflict resolution** | Unstated | Explicit protocol: when sources contradict, report both + evidence strength |
| **Prompt security** | Unstated | Three-layer injection defense, SSRF protection, sanitized at every boundary |
| **Adaptability** | Fixed plan, user can edit before execution | Autonomous mid-flight re-planning based on evidence quality |
| **Visualization** | Native charts (cosmetic — generated alongside text) | Evidence-grounded charts (data-backed — generated from structured evidence graph) |
| **Multi-agent** | Single agent, extended compute | Specialist swarm with adversarial tension between roles |
| **Customization** | MCP tool definitions | Context profiles (tone, domains, gaps) + MCP + per-task temperature tuning |

**The core thesis:** Google's advantage is scale (search index, compute budget, Gemini). Your advantage is *epistemic rigor* — the agent actively tries to be wrong and corrects itself. That's a moat that more compute doesn't close.

---

## Part 7: Strategic Positioning — Generalized Engine, Business-Specific Configuration

### Decision: Stay Generalized Engine, Deepen Business Configuration

**Agreed with user 2026-04-21.**

### Current Architecture

The agent is already positioned correctly:

- **Engine (31 modules, 1040 tests):** 100% generic — no PFE-specific logic anywhere in the code
- **Business specificity:** Lives entirely in `contexts/pfe.md` — a 278-line YAML+markdown context profile that injects blocked domains, extract domains, synthesis tone, report templates, and full business context into prompts
- **Design pattern:** Drop a new `.md` file in `contexts/` and the agent becomes specialized for any domain

The engine doesn't know about Pacific Flow, weddings, or San Diego. It knows about searching, filtering, verifying, and synthesizing. Context files tell it *what to care about*.

### Why This Is The Right Call

1. **Multiple businesses need different research contexts.** AGM (direct-to-consumer artist brand) and PFE (B2B consultancy) need different competitive intelligence. Same engine, different lens.
2. **Other projects consume the same engine.** PF-Intel, GigPrep, Gig Lead Responder all do some form of research. A generalized engine means they all consume it via MCP or the Python API. Business specificity comes at the integration layer.
3. **The "10 steps ahead" features are all generic capabilities.** Adversarial counter-search, evidence graphs, confidence scoring — none are industry-specific. Business value comes from combining them with rich context profiles.
4. **The moat compounds in both directions.** Engine gets smarter generically. Context profiles get deeper per business need.

### Where To Invest Business Specificity: Richer Context Profiles

Current `ContextProfile` has 4 fields (`blocked_domains`, `extract_domains`, `gap_schema`, `synthesis_tone`). The H2/H3 features create opportunities to make this dramatically richer without hardcoding business logic:

| Feature | Context Profile Extension |
|---------|--------------------------|
| Research memory (C35) | Per-context knowledge graph — PFE remembers competitor pricing across runs |
| Confidence scoring (C33) | Per-context confidence thresholds — "flag anything about pricing that's inferred, not documented" |
| Counter-search (C32) | Per-context adversarial prompts — "always verify claims about venue exclusivity deals" |
| Multi-source fusion (C38) | Per-context data sources — PFE pulls from WeddingWire + TheKnot + Yelp; AGM from Instagram + YouTube |
| Swarm roles (C39) | Per-context specialist roles — PFE gets a "venue intelligence" agent; a biotech context gets a "clinical trials" agent |

### Context Profile Roadmap

By end of H2, the `contexts/` directory should contain:

| File | Purpose |
|------|---------|
| `contexts/pfe.md` | Competitive intelligence for Pacific Flow Entertainment (exists) |
| `contexts/agm.md` | Artist brand competitive analysis for Alex Guillen Music |
| `contexts/venue-intel.md` | Venue-specific research (load-in, sound policy, coordinator preferences) |
| `contexts/general.md` | No business context — pure research mode |

The engine stays the same. The contexts make it yours.

### Positioning Spectrum

```
Pure Generic ←————————————————→ Pure Business Tool
         ↑
    HERE (and staying)
    
    Engine: generic
    Configuration: business-specific
    Integration: business-specific (MCP → PF-Intel, GigPrep, etc.)
```

---

## Part 8: Effort Estimate

| Horizon | Cycles | Sessions | Lines (est) | Calendar (2 sessions/week) |
|---------|--------|----------|-------------|---------------------------|
| H1: Foundation (C29-31) | 3 | 11 | ~470 | ~6 weeks |
| H2: Structural Leap (C32-35) | 4 | ~22 | ~800 | ~11 weeks |
| H3: Experience Layer (C36-39) | 4 | ~18 | ~600 | ~9 weeks |
| **Total** | **11** | **~51** | **~1870** | **~26 weeks** |

This is ambitious. The full vision is ~6 months at 2 sessions/week. But H1 alone (6 weeks) delivers significant value, and H2 (the structural leap) is where you pull ahead of Google.

---

## Feed-Forward

- **Hardest decision:** Whether to build a business-specific tool or a generalized engine. Chose generalized engine with rich business configuration because: (1) multiple brands need different research contexts, (2) other projects consume the same engine via MCP, (3) the "10 steps ahead" features are all generic capabilities. User agreed 2026-04-21.
- **Rejected alternatives:** (1) Scrapping C29-31 to jump straight to swarm architecture — too fragile without the epistemic foundation. (2) Building visualization first for demo value — cosmetic without structured evidence data to visualize. (3) Treating this as a rewrite — the existing pipeline is solid; this is additive. (4) Building a PFE-specific tool — locks out other projects and brands. (5) Interleaving H2 features with H1 — dependency chain is real, building confidence scoring without evidence-tier labeling is building on sand.
- **Least confident:** The swarm architecture (C39) is conceptually clear but architecturally untested at this scale in this codebase. The shared-spec pattern from sandbox validated 6 agents, but research swarm roles have richer interdependencies than web app agents. The 7+ agent boundary from the sandbox solution doc is a real unknown.

## Three Questions

1. **Hardest decision in this session?** Generalized vs. business-specific positioning. The PFE context file is so rich (278 lines of business intelligence) that it was tempting to lean into building a "PFE intelligence tool." But the architecture already separates engine from configuration correctly — the right move is to deepen that separation, not collapse it.
2. **What did you reject, and why?** Interleaving H2 features into H1. The dependency chain from the entropy roadmap is validated across 6 cycles — C29's evidence-tier labeling is a prerequisite for C33's confidence scoring. Breaking the chain to ship a flashy feature sooner risks building on a leaky pipeline.
3. **Least confident about going into the next phase?** The `ContextProfile` extension roadmap. Right now it has 4 fields and works cleanly. By H2 it needs per-context knowledge graphs, confidence thresholds, adversarial prompts, and data source definitions. That's a significant expansion of the context system that could become unwieldy if not carefully designed. The plan phase needs to nail the `ContextProfile` data model evolution.
