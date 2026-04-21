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

### Invariants (must not change across all horizons)

- All 1040+ existing tests pass after every cycle
- Existing CLI flags and MCP tools work unchanged
- Existing context files (`contexts/pfe.md`) work without modification
- No PFE-specific logic enters the engine code
- Additive pattern: new modules layer on, never change downstream module interfaces
- Report format remains backward compatible (new markers like `[Disputed]` are additive)

### Horizon 1: Complete the Foundation (C29-31, ~11 sessions)

**What:** Finish the entropy roadmap as planned.
**Why:** These are small, validated, dependency-ordered fixes. Every "10 steps ahead" feature becomes easier with these in place. Skipping them means building on a leaky pipeline.
**Risk of skipping:** Evidence-tier labeling doesn't exist yet. Skeptic findings aren't enforced yet. Building a swarm on top of non-enforced verification is theatre.

**Modifications for the new vision:**
- C29: When implementing evidence-tier labeling, design the data model to be extensible to per-claim confidence scores (don't just use inline text markers — output structured data too)
- C31: When implementing MCP tools, also add **inbound** MCP consumption (not just outbound tools) — this is the #9 fusion foundation
- C31: Expand novelty decomposition to be the seed for the contrarian agent role

### Horizon 2: The Structural Leap (C32-35, ~23 sessions)

**What:** The unique capabilities that make this agent categorically different from Deep Research Max.

**Revised ordering** (based on dependency analysis and impact ranking — see Appendix E):

| Cycle | Feature | Sessions | Confidence | Why This Position |
|-------|---------|----------|------------|-------------------|
| **32** | **Adversarial counter-search** — after draft, search for evidence against each major claim | 5 | 80% | Lowest implementation risk, immediate report quality gain. Extends existing skeptic with real counter-evidence. Quick win to validate H2 approach. |
| **33** | **Epistemic confidence scoring** — every claim gets a confidence level with evidence type, output as structured data + JSON sidecar | 6 | 75% | Builds the data model that memory needs. Consumes C32's counter-evidence flag. Every claim gets structured confidence before persistence. |
| **34** | **Research memory that compounds** — persistent knowledge graph queried at the start of every new run | 6 | 60% | **Moved up from C35.** Highest workflow impact — the agent gets smarter over time. Ships after C33 so memory stores confidence-scored claims from day one (no migration). |
| **35** | **Adaptive mid-flight re-planning** — agent adjusts strategy based on evidence quality mid-run | 6 | 65% | **Moved to last.** Highest risk, most internal. Benefits from all prior infrastructure. Confidence data (C33) + research memory (C34) give the planner maximum information. |

**H2 dependency chain:** C32-35 form a real sequential dependency, not a parallel set:

```
C29 → C32 (needs skeptic severity markers to prioritize claims)
     → C33 (needs C32's counter_evidence flag on ClaimConfidence)
       → C34 (needs C33's structured claims to store; without them, stores raw text)
         → C35 (needs C33's confidence_spread + C34's prior knowledge for planning)
```

C35 (adaptive planning) also overlaps existing `iterate.py` and `coverage.py` — both already do post-synthesis gap analysis and query refinement. C35 generalizes these from "one retry" to "continuous adaptive loop," which means it is not an isolated module addition.

**"Only ship 2" — two different answers depending on the goal:**

- **Moat pair (C32 + C33):** Counter-search + confidence scoring. These are the capabilities no competitor has. Together they make every report adversarially verified and epistemically auditable. Best for differentiation.
- **Workflow pair (C33 + C34):** Confidence scoring + research memory. These create a compounding feedback loop — confidence-scored claims are stored, next run queries them, agent focuses on uncertain areas. Best for the PFE competitive intelligence use case where the same topics are researched repeatedly.

**Why these four first:**
- They're all **epistemic** — they make the agent's thinking better, not just its output prettier
- They build on C29-31 directly (clear dependency chain)
- Google can't easily copy them because they require adversarial design, not just bigger models
- They're the moat: bigger models don't solve "actively try to disprove yourself"
- No competitor has: active counter-search, per-claim epistemic provenance, cross-session research memory with staleness, or frame-questioning verification

**New modules created:** `confidence.py` (C33), `knowledge.py` (C34), `planner.py` (C35)

See Appendix B for full cycle specs (acceptance criteria, dependencies, design notes).

### Horizon 3: The Experience Layer (C36-39, ~18 sessions)

**What:** The capabilities that make the output beautiful and the agent accessible.

| Cycle | Feature | Why This Order |
|-------|---------|----------------|
| **36** | **Streaming reasoning trace** — real-time visibility into agent thinking, stored as persistent log | Parity with Google. Low-risk. Makes the agent feel alive. |
| **37** | **Native visualization** — charts, timelines, relationship maps generated from structured evidence data | Requires evidence graph from H2. Now visualizations show real data, not cosmetic charts. |
| **38** | **Multi-source data fusion** — inbound MCP + web + local files, with conflict resolution protocol | Requires C31 MCP foundation + H2 confidence scoring to resolve conflicts. |
| **39** | **Multi-agent research swarm** — parallel specialist agents (domain, contrarian, verifier, editor) | The capstone. Requires H2 epistemic infrastructure so each agent role is meaningful. |

**Swarm architecture (C39) — key decisions from research (see Appendix D):**
- **5 core roles:** Coordinator, Domain Expert ×N, Contrarian, Verifier, Editor + 2 optional (Temporal Analyst, Context Specialist)
- **Communication:** Phased blackboard (in-memory dict), reads only at phase boundaries. Same async pattern as `skeptic.py`
- **Minimum viable swarm (MVS):** 4 roles — Coordinator + 2 Domain Experts + Editor. Proves parallel facet research before adding adversarial roles
- **Skeptic in MVS: unified post-synthesis pass preserved.** The current `skeptic.py` three-lens pass runs after synthesis. The MVS keeps this unchanged — distributing skeptic lenses across swarm roles (evidence→Verifier, timing→Temporal, frame→Contrarian) is a later evolution (C39b+) that requires validating whether separated lenses maintain the same adversarial quality as the combined pass
- **Shared spec:** ~130 lines (within sandbox validated range). Three sections: data contracts, phase contracts, behavioral contracts
- **7+ agent boundary:** Max depth 6 with parallel Contrarian + Temporal. Never exceed 7 without isolated experiment

**Why these are last:**
- Streaming and visualization are presentation — they make good research *look* good, but don't make research *better*
- Fusion and swarm are architecturally complex and benefit most from all prior infrastructure
- The swarm specifically needs: adversarial counter-search (contrarian role), confidence scoring (verifier role), adaptive planning (coordinator role), and research memory (shared context)

---

## Part 6: What This Gives You Over Deep Research Max

| Dimension | Deep Research Max | Your Agent (After H1-H3) |
|-----------|------------------|--------------------------|
| **Epistemic integrity** | Unverified — no adversarial self-check | Triple-verified: skeptic → counter-search → confidence scoring |
| **Learning** | Stateless — every run starts from zero | Compounds — knowledge store grows with every query |
| **Transparency** | Streams thinking but doesn't persist or structure it | Persistent reasoning trace + per-claim confidence levels |
| **Source quality** | Unstated | Five-layer gate: vague detection → relevance scoring → source tiers → diversity gate → skeptic |
| **Conflict resolution** | Unstated | Explicit protocol: when sources contradict, report both + evidence strength |
| **Prompt security** | Unstated | Three-layer injection defense, SSRF protection, sanitized at every boundary |
| **Adaptability** | Fixed plan, user can edit before execution | Autonomous mid-flight re-planning based on evidence quality |
| **Visualization** | Native charts (cosmetic — generated alongside text) | Evidence-grounded charts (data-backed — generated from structured evidence graph) |
| **Multi-agent** | Single agent, extended compute | Specialist swarm with adversarial tension between roles |
| **Customization** | MCP tool definitions | Context profiles (tone, domains, gaps) + MCP + per-task temperature tuning |

**The core thesis:** Google's advantage is scale (search index, compute budget, Gemini). Your advantage is *epistemic rigor* — adversarial verification, per-claim confidence scoring, and auditability. This is a positioning advantage, not a permanent moat: it holds as long as commercial incentives discourage competitors from adding self-doubt to their reports. The structural defense is that adversarial verification is woven through the pipeline (not bolted on), making it costly to replicate without rearchitecting.

---

## Part 7: Strategic Positioning — Generalized Engine, Business-Specific Configuration

### Decision: Stay Generalized Engine, Deepen Business Configuration

**Agreed with user 2026-04-21.**

### Current Architecture

The agent is already positioned correctly:

- **Engine (31 modules, 1040 tests):** 100% generic — no PFE-specific logic anywhere in the code
- **Business specificity:** Lives entirely in `contexts/pfe.md` — a 278-line YAML+markdown context profile that injects blocked domains, extract domains, synthesis tone, report templates, and full business context into prompts
- **Design pattern:** A context package (`.md` file in `contexts/` plus optional auxiliary YAML files for gaps, memory, sources) specializes the agent for any domain

The engine doesn't know about Pacific Flow, weddings, or San Diego. It knows about searching, filtering, verifying, and synthesizing. Context files tell it *what to care about*.

### Why This Is The Right Call

1. **Multiple businesses need different research contexts.** AGM (direct-to-consumer artist brand) and PFE (B2B consultancy) need different competitive intelligence. Same engine, different lens.
2. **Other projects consume the same engine.** PF-Intel, GigPrep, Gig Lead Responder all do some form of research. A generalized engine means they all consume it via MCP or the Python API. Business specificity comes at the integration layer.
3. **The "10 steps ahead" features are all generic capabilities.** Adversarial counter-search, evidence graphs, confidence scoring — none are industry-specific. Business value comes from combining them with rich context profiles.
4. **The moat compounds in both directions.** Engine gets smarter generically. Context profiles get deeper per business need.

### Where To Invest Business Specificity: Richer Context Profiles

Current `ContextProfile` has 4 fields (`blocked_domains`, `extract_domains`, `gap_schema`, `synthesis_tone`). The H2/H3 features grow this to 10 fields — but with a strict simplicity constraint (see Appendix C for full data model).

**Simplicity constraint: the "5-minute context test."** If a new context author can't understand and correctly fill in a field within 5 minutes of reading a one-line YAML comment, the field is too complex for the profile. Complex behavior gets a file-path reference (like `gap_schema` already does).

**Evolution path:**

| Horizon | New Fields | Pattern |
|---------|-----------|---------|
| **H1 (C29-31)** | `evidence_tier_overrides`, `skeptic_focus` | Inline YAML — simple lists and key-value pairs |
| **H2 (C32-35)** | `confidence_flag_threshold` (inline), `knowledge_store` (file-path) | Inline int + directory reference for persistent memory |
| **H3 (C36-39)** | `source_config` (file-path), `swarm_roles` (file-path) | File-path references — complex subsystems live in separate YAML files |

**Final field count: 10** (4 existing + 2 H1 + 2 H2 + 2 H3). All default to empty/zero — zero migration needed. Existing `pfe.md` works untouched at every horizon.

**Dropped from earlier proposal:** `preferred_sources` — Cycle 24 explicitly rejected `preferred_domains` because +0.5 on int scores with int cutoff is a no-op. The same issue applies unless the scoring model changes. If C29's score-aware refinement creates a real mechanism for source preference, the field can be added then. `source_config` moved from H2 to H3 because no H2 cycle consumes it (multi-source fusion is C38).

**The complexity boundary:** If data is declarative, static, and fits in a YAML list → inline. If data is procedural, mutable, or has internal structure → file-path reference.

**Path governance rules:**
1. **One-hop only.** A context profile references auxiliary files directly. Auxiliary files must not reference further files (no chained references).
2. **Shared validation.** All file-path fields use the same two-layer defense from Cycle 24: character rejection (no `..`, no absolute paths, no null bytes) at parse time + `resolve()` + `is_relative_to(project_root)` containment at runtime.
3. **Read-only vs read/write.** `gap_schema`, `source_config`, `swarm_roles` are read-only — the engine never modifies them. `knowledge_store` is the only writable path. It points to a directory (not a file) where the engine appends per-run JSON entries via `atomic_write()`.
4. **Writable path containment.** `knowledge_store` directories must resolve inside the project root. The engine creates the directory if it doesn't exist but never writes outside it. Per-context isolation (`knowledge_store: memory/pfe`) prevents cross-context data leakage.

**Directory layout after H2:**
```
contexts/          # context profiles (read-only)
  pfe.md, agm.md, venue-intel.md, general.md
memory/            # knowledge stores (read/write, C34)
  pfe/             # per-context scoped directory of JSON entries
gaps/              # gap schemas (read-only, existing)
  pfe.yaml
```

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

## Part 8: Competitive Landscape Summary

Full analysis in Appendix A. Key findings:

**The epistemic rigor moat holds.** Commercial products (Google, OpenAI, Perplexity) are incentivized to produce confident-sounding reports. Adversarial self-verification produces reports that sometimes say "we're not sure" — epistemically correct but commercially unappealing. They're unlikely to voluntarily add this.

**Biggest risk: search index dependency.** Google queries the full Google Search index directly. You depend on Tavily + DuckDuckGo. Mitigation: add Exa as a semantic search provider (C38), and include "search coverage confidence" in C33's confidence scoring.

**No competitor has:** active counter-search, per-claim epistemic provenance, context-isolated synthesis, cross-session research memory with staleness, or frame-questioning verification.

**Quick wins to adopt from competitors:**
- **Collaborative planning** (`--plan-review` flag) — low effort, closes visible gap with Google
- **Exa as third search provider** — semantic/conceptual queries where Tavily's keyword results are weak
- **Code execution during research** — consider for H3 (OpenAI's genuine differentiator)
- **Study Perplexity's citation UX** — gold standard for inline citations when visualization ships

**Competitive position matrix:**

| Dimension | Google | OpenAI | Perplexity | GPT-Researcher | **Your Agent (H1-H3)** |
|-----------|--------|--------|------------|----------------|------------------------|
| Adversarial verification | None | None | None | Same-frame review | **Three-lens + counter-search** |
| Evidence provenance | None | None | Source-level | None | **Per-claim tier labeling** |
| Cross-session memory | None | None | None | None | **Gap schema + knowledge store** |
| Prompt injection defense | Unstated | Acknowledged | Unstated | None | **Three-layer defense** |
| Search coverage | Full Google index | Web browsing | Multi-source | Any provider | Tavily + DDG (expandable) |
| Visualization | Native charts | None | None | PDF/DOCX | Planned (C37) |
| Customization | MCP tools | None | None | LLM choice | **Context profiles + modes** |

---

## Part 9: Effort Estimate (Revised)

| Horizon | Cycles | Sessions | Lines (est) | New Modules | Calendar (2 sessions/week) |
|---------|--------|----------|-------------|-------------|---------------------------|
| H1: Foundation (C29-31) | 3 | 11 | ~470 | 0 | ~6 weeks |
| H2: Structural Leap (C32-35) | 4 | 23 | ~1135 | 3 (`confidence.py`, `knowledge.py`, `planner.py`) | ~12 weeks |
| H3: Experience Layer (C36-39) | 4 | ~18 | ~600 | TBD | ~9 weeks |
| **Total** | **11** | **~52** | **~2205** | **3+** | **~27 weeks** |

H2 is larger than initially estimated (23 sessions vs ~22, ~1135 lines vs ~800) due to detailed scoping revealing 26 individual items across 4 cycles. But H1 alone (6 weeks) delivers significant value, and H2 is where you pull ahead of Google.

---

## Feed-Forward

- **Hardest decision:** H2 ordering. The chain C29→C32→C33→C34→C35 is a real sequential dependency (each cycle's output feeds the next), not a parallel set. Ordered by dependency + risk: counter-search first (lowest risk, extends existing skeptic), confidence scoring second (builds data model), memory third (stores structured data), adaptive planning last (highest risk, overlaps existing iterate/coverage logic).
- **Rejected alternatives:** (1) Scrapping C29-31 to jump to swarm — too fragile without epistemic foundation. (2) Visualization first for demo value — cosmetic without evidence graph. (3) PFE-specific tool — locks out other projects. (4) Research memory before confidence scoring — would store unstructured data and need migration later. (5) LLM-driven adaptive planning — explicit rules are deterministic, testable, and cheaper. (6) SQLite for knowledge store — codebase has zero database dependencies. (7) Distributing skeptic across swarm roles in MVS — unvalidated; keep unified post-synthesis pass. (8) `preferred_sources` on ContextProfile — same no-op as C24's `preferred_domains`.
- **Least confident (ranked):**
  1. **Search coverage dependency** — the entire epistemic rigor thesis sits on top of Tavily + DuckDuckGo results. If coverage is thin, adversarial verification operates on an incomplete evidence base. Partially mitigated by C38 (Exa), but structurally unfixable without a search index. C33 should include a "coverage confidence" dimension.
  2. **Adaptive planning (C35, 65% confidence)** — replacing `_research_deep()`'s fixed two-pass with a dynamic loop is the riskiest refactor, and it overlaps existing `iterate.py`/`coverage.py` logic that must be carefully reconciled, not duplicated.
  3. **Confidence extraction prompt (C33)** — asking Claude to score its own claims is metacognitive and less studied than evidence-tier labeling. Plan phase needs to prototype with 5 real reports.

## Three Questions

1. **Hardest decision in this session?** H2 cycle ordering. Five agents produced competing recommendations. Reconciled by verifying the actual code: C32-35 form a real dependency chain (each cycle's data model feeds the next), not a parallel set as initially claimed. The chain C29→C32→C33→C34→C35 is load-bearing.
2. **What did you reject, and why?** (a) `preferred_sources` on ContextProfile — C24 proved the +0.5 score boost is a no-op with int scores and int cutoffs. Don't add fields with zero effect. (b) Distributing skeptic lenses across swarm roles in the MVS — the current `skeptic.py` runs three lenses as a unified post-synthesis pass. Splitting them across roles is an unvalidated change; keep the proven pattern in v1. (c) `source_config` in H2 — no H2 cycle consumes it; moved to H3/C38.
3. **Least confident about going into the next phase?** Search coverage dependency. The brainstorm claims epistemic rigor as the differentiator, but every verification layer operates on whatever Tavily/DDG return. If they miss a key source, counter-search can't find it either. This is a structural limitation, not a fixable bug. The plan phase must decide whether to include "coverage confidence" in C33's scoring model or flag it as an accepted risk.

---

## Research Appendices

Detailed research produced by 5 parallel agents on 2026-04-21. These feed into the Plan phase.

| Appendix | File | Contents |
|----------|------|----------|
| A | [Competitive Landscape](appendices/appendix-a-competitive-landscape.md) | Google, OpenAI, Perplexity, Exa, Tavily, open-source agents. Position matrix. Moat analysis. |
| B | [H2 Detailed Cycle Specs](appendices/appendix-b-h2-cycle-specs.md) | C32-35 at entropy-roadmap depth: modules, acceptance criteria (EARS), dependencies, design notes. 26 items, ~1135 lines. |
| C | [ContextProfile Evolution](appendices/appendix-c-context-profile-evolution.md) | Data model from 4→10 fields. Migration path. Simplicity constraints. File-path reference pattern. |
| D | [Swarm Architecture](appendices/appendix-d-swarm-architecture.md) | 5 roles, blackboard pattern, shared spec (~130 lines), MVS (4 roles), pipeline mapping. |
| E | [H2 Prioritization Analysis](appendices/appendix-e-h2-prioritization.md) | Dependency graph, impact ranking, alternative orderings, "only ship 2" test. |
