# Master Recommendations: Future Build Cycles for the Research Agent

**Date:** 2026-02-15
**Inputs:** All 13 research documents in `docs/research/`, `LESSONS_LEARNED.md`
**Purpose:** Synthesize every research finding into a prioritized roadmap for the agent's next development phases

---

## Executive Summary

After 17 cycles of development, the research agent has a solid core: a stateless pipeline that decomposes queries, searches the web, fetches/extracts content, summarizes with Claude, runs adversarial verification, and synthesizes structured reports. It has unique differentiators (three-lens skeptic, context-isolated synthesis, SSRF/prompt injection defense) that no other open-source research agent matches.

The research documents collectively point to **three strategic phases** for what comes next:

1. **Make the agent stateful** — gap schemas, state persistence, staleness detection (Cycles 17A-17D, already planned)
2. **Make the agent accessible** — pip packaging, MCP server, REST API (Cycles 18-20)
3. **Make the agent smarter** — multi-provider search, delta output, multi-property support (Cycles 21+)

---

## Phase 1: Stateful Foundation (Cycles 17A-17D)

**Status:** Fully planned in `cycle-17-05-cycle-breakdown.md`
**Estimated effort:** ~910 lines across 4 sub-cycles

This is the most thoroughly researched phase. Five documents (17-01 through 17-05) provide codebase analysis, best practices, failure modes, edge cases, and a sequential breakdown. The plan is sound. Key points:

### What It Builds

| Cycle | Theme | Key Deliverable |
|-------|-------|-----------------|
| 17A | Foundation infrastructure | Error hierarchy, `ContextResult` type, token budgeting, atomic writes |
| 17B | Gap schema layer | YAML parser, validator, cycle detector, priority sorter |
| 17C | State persistence + staleness | State writer, timestamp management, staleness detection, batch limiter, audit log |
| 17D | Pipeline integration | Context refactor, budget enforcement, relevance gate extension, pre/post-research hooks |

### Top Risks to Watch

From the failure mode analysis (17-03), these are the highest-impact risks:

| Risk | Severity | Mitigation |
|------|----------|------------|
| Context window budget war (F5.2) | CRITICAL | Token budget utility in 17A, enforced in 17D |
| Error cascade across features (F5.1) | CRITICAL | Distinct exception types in 17A |
| Malformed schema crashes (F2.1) | CRITICAL | Validator reports ALL errors in 17B |
| Cascading status flips (F4.1) | CRITICAL | Per-gap TTL without dependency cascade in 17C |
| State file corruption (F4.4) | CRITICAL | Atomic writes in 17A |

### Recommendation

**Execute 17A-17D as planned.** The research is thorough and the sequencing is well-reasoned. One adjustment: consider adding a lightweight `CycleConfig` dataclass (suggested in edge case analysis) during 17A to centralize `max_gaps_per_run`, `max_tokens_per_prompt`, and other batch limits.

---

## Phase 2: Accessibility (Cycles 18-20)

**Source:** `research-agent-integrations.md`, `cycle-17-integration-assessment.md`

The integration assessment is clear: **do 17A-17D first, then integrate.** The reasoning is sound — integrations expose the pipeline externally, and the pipeline is changing during 17A-17D.

### Cycle 18: Pip-Installable Package

**Priority: HIGH** | Effort: LOW

- Mostly packaging (`pyproject.toml`, clean `__init__.py` exports)
- Forces definition of a clean public API surface
- GPT-Researcher's pip install is their #2 interface after CLI
- Prerequisite for MCP and REST API

**What to build:**
- `pyproject.toml` with proper entry points
- Clean `__init__.py` that exports `ResearchAgent`, `ResearchMode`, and key types
- Version management
- README with installation and quick-start instructions

### Cycle 19: MCP Server

**Priority: HIGH** | Effort: MEDIUM

MCP is the dominant protocol for LLM tool access — adopted by Anthropic, OpenAI, Google DeepMind, and Microsoft. Building an MCP server gives integration with Claude Code, Cursor, and other LLM clients for free.

**What to build:**
- MCP server exposing `search`, `fetch`, `synthesize` as tools
- GPT-Researcher's `gptr-mcp` as reference implementation
- Tool schemas following MCP specification
- Structured error returns using 17A's exception hierarchy

**Key insight from research:** Firecrawl's MCP averages 7s runtime and 83% accuracy. Anthropic's Tool Search reduces context consumption by 85%. These benchmarks set the bar for performance.

### Cycle 20: REST API

**Priority: MEDIUM** | Effort: MEDIUM-HIGH

- FastAPI wrapper with async endpoints
- Polling for long-running research (follow Exa's async pattern)
- Authentication and rate limiting
- Cost tracking per request (leveraging 17A's token budget)

### Cycle 20+: Workflow Hooks

**Priority: LOW** | Effort: LOW (once REST API exists)

- Zapier/n8n integration via webhooks
- Scheduled or triggered research
- Depends on REST API

### Recommendation

**Cycle 18 (pip package) is the critical enabler.** It's low effort and unlocks everything else. Do it immediately after 17D. MCP server (Cycle 19) should follow quickly — the market is moving fast on MCP adoption.

---

## Phase 3: Intelligence Upgrades (Cycles 21+)

**Sources:** `2026-02-05-research-agent-best-practices.md`, `research-agent-features-2025-2026.md`, `research-ai-agents-comprehensive-2025-2026.md`, `generalized-vs-niche-research-agents.md`

These are the features that make the agent meaningfully more capable, ordered by impact and feasibility.

### Cycle 21: Multi-Provider Search Strategy

**Priority: HIGH** | Effort: MEDIUM

The best practices research is emphatic: **use multiple specialized retrievers, not just general web search.** The current Tavily + DuckDuckGo stack is solid but limited.

**What to build:**
- **Exa** as a semantic/neural search option for conceptual queries
- **Serper** as a high-volume budget fallback
- Provider routing: Tavily for quality, Exa for research depth, Serper for volume
- Circuit breaker pattern for provider failures (from best practices research)
- Cost-aware routing: cheaper providers for sub-queries, premium for primary

**Key data points:**
| Provider | Best For | Cost/1K |
|----------|----------|---------|
| Tavily | AI agents, RAG | $8 |
| Exa | Semantic/neural | $5 |
| Serper | Volume/budget | $0.30-$1.00 |
| Brave | Privacy, independent index | $3-5 |

**Note:** Bing Search API retired August 2025. Avoid any Bing dependencies.

### Cycle 22: Google Drive Context Loading

**Priority: MEDIUM** | Effort: MEDIUM

Deferred from Cycle 17 due to external dependency risk. The `ContextResult` API from 17A is designed so Drive loading slots in by replacing the file reader — no pipeline changes needed.

**What to build:**
- OAuth2 authentication flow
- Google Docs → Markdown conversion
- Caching layer (avoid re-fetching unchanged docs)
- Section validation with warnings for renamed/missing sections

**Top risks (from 17-03):**
- OAuth token expiry mid-pipeline (F1.2)
- Context overflow from large docs (F1.1) — mitigated by 17A's token budget
- Rich text conversion fidelity (F1.4)

### Cycle 23: Delta-Only Intelligence Output

**Priority: MEDIUM** | Effort: HIGH

The hardest feature in the pipeline. The failure mode analysis flags semantic diff accuracy (F3.2) as "fundamentally hard with no clean solution."

**Recommended approach:**
1. Start with **structural diff** — section-by-section comparison between consecutive reports
2. Use `last_checked` vs `last_verified` timestamps from 17C to distinguish "searched and found nothing new" from "haven't looked yet"
3. Defer **semantic diff** (detecting meaningful changes in rephrased content) to a later cycle
4. Handle the bootstrap problem: first run saves state for future deltas, generates a full report

**What NOT to build yet:**
- LLM-powered semantic comparison (high cost, unpredictable accuracy)
- Automatic delta delivery (email/Slack) — too many moving parts

### Cycle 24: Swappable Context Profiles

**Priority: MEDIUM** | Effort: LOW-MEDIUM

From the generalized-vs-niche analysis: the agent is a "general engine with a niche configuration layer." Push that further.

**What to build:**
- Profile system replacing single `research_context.md`
- One profile per client/domain (e.g., `profiles/pacific-flow.md`, `profiles/client-b.md`)
- CLI flag: `--profile pacific-flow`
- Profile includes: business context, domain-specific source preferences, synthesis instructions, gap schema path

**Key principle:** Keep the engine general, push specialization into configuration and prompts. Avoid rebuilding the pipeline for each niche.

### Cycle 25: Multi-Property Support

**Priority: LOW** | Effort: HIGH

From edge case analysis (Edge Case 8): the user manages multiple properties/brands and wants to research all in a single cycle.

**What to build:**
- Property-scoped state (gap schemas, baselines, timestamps per property)
- Execution orchestrator above `ResearchAgent`
- Cross-property deduplication (shared search results)
- Per-property error boundaries and cost tracking

**Start with:** Strict isolation per property. Shared intelligence (cross-property findings) is a feature, not a prerequisite.

---

## Competitive Positioning

### What Sets This Agent Apart (Protect These)

From `unique-features-analysis.md`, these are the differentiators to **maintain and strengthen**:

1. **Three-lens adversarial skeptic** — No other agent questions whether the analytical frame is wrong ("Break the Trolley"). Protect this uniqueness.
2. **Context-isolated two-pass synthesis** — Factual sections generated without business context. This is architecturally novel. Don't collapse into single-pass synthesis for convenience.
3. **Three-layer cascade recovery** — Domain-aware cost gating on Jina → Tavily Extract → snippet. Keep the cost intelligence.
4. **Three-way relevance gate** — `full_report` / `short_report` / `insufficient_data`. Expanding to five-way in 17D (adding `already_covered` and `no_new_findings`).
5. **Defense in depth** — Three-layer prompt injection defense + SSRF with DNS rebinding protection. Most agents cut corners here.

### Where Competitors Are Ahead (Close These Gaps)

| Gap | Who Does It Better | Priority |
|-----|-------------------|----------|
| Multi-provider search | GPT-Researcher (any search engine), Perplexity (multi-model routing) | Cycle 21 |
| MCP integration | GPT-Researcher (`gptr-mcp`), Exa, Firecrawl | Cycle 19 |
| Memory/state persistence | Letta (MemGPT), Mem0 | Cycles 17A-17D |
| PDF/academic parsing | LlamaParse, MinerU, Docling | Future |
| Interactive output (charts, visuals) | Google Gemini Visual Reports | Not aligned with CLI-first approach |
| Browser automation | OpenAI Operator, Skyvern, Browser Use | Complementary tool, not built-in |

### Market Context

From `research-ai-agents-comprehensive-2025-2026.md`:

- The agentic AI revolution is overwhelmingly **community-driven** — solo devs and small teams are building the most-starred and best-performing agents
- GPT-Researcher ($25M Series A), Lovable ($1.8B valuation), CrewAI (60% Fortune 500) all started as indie projects
- Task duration is doubling every 7 months — agents are handling increasingly complex, longer-running work
- MCP is becoming the HTTP of AI tool connectivity — don't ignore it
- 40%+ of agentic AI projects may be canceled by 2027 due to unclear value — **focus on demonstrable ROI, not features**

---

## Lessons That Should Inform Every Future Cycle

From `LESSONS_LEARNED.md` and the research corpus:

### Process

1. **Research before coding** — Every cycle that started with research (Cycles 7, 8, 9, 10, 17) produced better results than those that jumped into code
2. **Diagnose with real data** — Cycles 13 and 15 both improved dramatically when real query/response data was analyzed before changes were made
3. **Additive pattern** — New stages layer on without changing downstream modules. 17 cycles have followed this successfully
4. **Score the unit you decide on** — Cycle 15's insight. If you filter sources, score sources (not chunks). If you prioritize gaps, score gaps (not categories)

### Architecture

5. **Separate deterministic control from non-deterministic reasoning** — This eliminates 44.2% of system design issues (from best practices research)
6. **Context engineering is non-negotiable** — Every token competes for attention. The token budget system (17A) must be enforced ruthlessly
7. **"Missing" vs "failed" vs "empty" are three different states** — The current `None` return conflates all three. The `ContextResult` type (17A) fixes this for context; apply the same pattern everywhere
8. **Atomic writes for any persistent state** — One-line fix that prevents the most catastrophic corruption scenarios

### What NOT to Build

9. **No fuzzy section matching yet** — Start with exact matching + clear warnings. Solve with documentation first.
10. **No automated scheduling yet** — Race condition risks outweigh benefits until locking is in place
11. **No LLM-powered search suggestions yet** — Hardcoded suggestions per gap category first
12. **No cross-property intelligence sharing yet** — Strict isolation first, shared intelligence later

---

## Recommended Cycle Sequence

| Cycle | Theme | Effort | Depends On |
|-------|-------|--------|------------|
| **17A** | Foundation infrastructure | ~190 lines | Nothing |
| **17B** | Gap schema layer | ~290 lines | 17A |
| **17C** | State persistence + staleness | ~240 lines | 17A, 17B |
| **17D** | Pipeline integration | ~190 lines delta | 17A, 17B, 17C |
| **18** | Pip-installable package | Low | 17D |
| **19** | MCP server | Medium | 18 |
| **20** | REST API | Medium-High | 18 |
| **21** | Multi-provider search | Medium | 17D |
| **22** | Google Drive context | Medium | 17D |
| **23** | Delta-only output | High | 17C, 17D |
| **24** | Swappable context profiles | Low-Medium | 17D |
| **25** | Multi-property support | High | 17C, 17D, 24 |

**Note:** Cycles 18-19 (accessibility) and 21-24 (intelligence) can be interleaved based on what's most valuable at the time. The sequence above is a recommendation, not a hard dependency chain.

---

## One-Line Summary

**The agent's core pipeline is strong and uniquely differentiated. The next phase is about making it stateful (17A-17D), then accessible (18-20), then progressively smarter (21+) — always protecting the adversarial quality control and defense-in-depth that set it apart.**
