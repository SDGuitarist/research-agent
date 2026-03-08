# Skills, Commands & Workflows — Cookbook-Inspired Brainstorm

**Date:** 2026-03-08
**Source:** Anthropic Claude Cookbook (`anthropics/anthropic-cookbook`) — Agent SDK, Tool Use, Skills, RAG, Summarization, Extended Thinking, Agent Patterns

---

## Cookbook Patterns Mapped to Research Agent

### Agent SDK Patterns (from `claude_agent_sdk/`)

| Pattern | Cookbook Example | Research Agent Mapping |
|---------|----------------|----------------------|
| **Stateless query()** | One-liner research agent | Parallel sub-query execution in `agent.py` |
| **Multi-agent orchestration** | Chief of Staff → subagents via `Task` tool | Orchestrator delegates to specialized research workers |
| **MCP server integration** | Git/GitHub MCP, SRE custom MCP | Already built (`mcp_server.py`), extend with new tools |
| **Evaluator-optimizer loop** | Generate → evaluate → feedback → regenerate until PASS | Maps to `skeptic.py` adversarial verification cycle |
| **Orchestrator-workers** | Dynamic task decomposition + parallel workers | Maps to `decompose.py` → parallel search/fetch |
| **Prompt chaining** | Sequential pipeline stages | Already the core architecture (additive stages) |
| **Routing** | Classify-then-dispatch | Maps to `decompose.py` SIMPLE/COMPLEX classification |
| **Parallelization** | ThreadPoolExecutor fan-out | Already in fetch; extend to summarization |

### Tool Use Patterns (from `tool_use/`)

| Pattern | How It Works | Application |
|---------|-------------|-------------|
| **Embedding-based tool search** | Embed tool definitions, semantic search at runtime | Search across saved reports by meaning, not filename |
| **Lazy tool loading** | `describe_tool` meta-tool, load on demand | Large tool sets for MCP server |
| **Pydantic schemas** | Auto-generate JSON schemas from models | Replace manual MCP tool schema definitions |
| **Parallel tool invocation** | `batch_tool` wraps multiple calls | Batch relevance scoring |
| **Programmatic Tool Calling (PTC)** | Claude writes code that calls tools | Batch source processing in single pass |
| **Context compaction** | `compaction_control` auto-summarizes history | Long-running research sessions |
| **Memory tool** | File-based persistent state across sessions | Cross-session research memory |
| **Structured extraction** | Tools as formatters (force JSON output) | Guaranteed structured relevance scores |

### Skills System (from `skills/`)

| Concept | How It Works | Application |
|---------|-------------|-------------|
| **Skill bundles** | SKILL.md + scripts + resources in a directory | Already using this pattern for queue/digest |
| **Skill composition** | Multiple skills combined in single request | Chain research + analysis + reporting skills |
| **Custom skills** | `custom_skills/` directory with programmatic loading | Domain-specific research workflows |
| **Skill registration** | `client.beta.skills.create()` from directory | Not directly applicable (Claude Code skills are markdown-based) |

### RAG & Summarization Patterns

| Pattern | How It Works | Application |
|---------|-------------|-------------|
| **Summary-indexed RAG** | Summarize → score relevance via summaries → retrieve full docs | Cache source summaries for faster re-research |
| **Reranking (Level 3)** | Claude re-scores retrieved chunks after initial retrieval | Add between `relevance.py` and `synthesize.py` — cookbook shows ~10% accuracy improvement |
| **Map-reduce summarization** | Cheap model per chunk → capable model for synthesis | Already doing this (Haiku chunks → Sonnet synthesis) |
| **Guided summarization** | Domain-specific framework in prompt | Context profiles already provide this |
| **LLM-as-judge evaluation** | Claude evaluates output quality on dimensions | Already in `critique.py`, could add A/B testing |

---

## Proposed New Skills

### 1. `/research:compare` — Report Comparison

**What:** Side-by-side comparison of 2-3 saved research reports.
**How:** Load reports → extract claims → cross-reference → surface contradictions, agreements, and gaps.
**Cookbook pattern:** LLM-as-judge + parallel tool invocation.
**Extension point:** New MCP tool `compare_reports` + skill instructions.
**Value:** Users often research the same topic over time; comparing old vs new reveals how the landscape changed.

### 2. `/research:deep-dive` — Recursive Depth Research

**What:** Takes a specific finding/claim from an existing report and recursively researches it.
**How:** Extract claim → decompose into verification queries → research each → synthesize with extended thinking.
**Cookbook pattern:** Evaluator-optimizer loop + extended thinking + tool use.
**Extension point:** New mode `ResearchMode.verify()` with high relevance cutoff and skeptic-first pipeline.
**Value:** Turns breadth research into depth research on demand.

### 3. `/research:monitor` — Ongoing Topic Monitoring

**What:** Periodic re-research on saved topics, alerting on significant changes.
**How:** Track topic + last research date → re-research at interval → diff reports → alert if >N claims changed.
**Cookbook pattern:** Memory tool (persistent state) + evaluator-optimizer (change detection).
**Extension point:** Reuses `staleness.py` + `schema.py` gap system.
**Value:** Competitive intelligence and trend tracking without manual re-runs.

### 4. `/research:briefing` — Multi-Report Executive Summary

**What:** Synthesize multiple saved reports into a single executive briefing.
**How:** Load N reports → extract key findings per report → meta-summarize → format per context profile.
**Cookbook pattern:** Meta-summarization (map-reduce) + guided summarization.
**Extension point:** New MCP tool + synthesis template.
**Value:** Decision-makers need one page, not five reports.

### 5. `/research:fact-check` — Standalone Adversarial Verification

**What:** Run skeptic verification on any document (not just research reports).
**How:** Extract claims → evidence agent + timing agent + framing agent → confidence scores.
**Cookbook pattern:** Multi-agent orchestration (Chief of Staff → specialized agents).
**Extension point:** Expose `skeptic.py` as standalone MCP tool and skill.
**Value:** Verify external documents, not just self-generated reports.

### 6. `/research:search-reports` — Semantic Report Search

**What:** Search across all saved reports by meaning, not filename.
**How:** Embed report summaries → cosine similarity search → return relevant sections.
**Cookbook pattern:** Embedding-based tool search.
**Extension point:** New MCP tool `search_reports`.
**Value:** "What did I research about X?" without remembering filenames.

---

## Proposed New MCP Tools

| Tool | Parameters | Returns | Pattern |
|------|-----------|---------|---------|
| `compare_reports` | `filenames: list[str]` | Contradiction/agreement analysis | Parallel invocation |
| `search_reports` | `query: str, top_k: int` | Ranked report sections | Embedding search |
| `research_chain` | `query: str, depth: int` | Multi-pass research result | Agentic loop |
| `verify_claim` | `claim: str, sources: int` | Evidence assessment + confidence | Evaluator-optimizer |
| `suggest_context` | `query: str` | Recommended context profile | Classification/routing |
| `batch_research` | `queries: list[str], mode: str` | Multiple reports | Parallel + PTC |

---

## Proposed New Research Modes

| Mode | Sources | Relevance Cutoff | Special Features | Cost Est. |
|------|---------|-----------------|-----------------|-----------|
| `--exploration` | 20 | 2 (low) | No skeptic, broad search, landscape template | ~$0.60 |
| `--verify` | 6 | 4 (high) | Skeptic-first, extended thinking, claim-focused | ~$0.35 |
| `--competitive` | 10 | 3 | Domain-filtered, comparative template | ~$0.50 |
| `--academic` | 8 | 3 | Scholar cascade, citation-heavy template | ~$0.40 |

---

## Proposed Workflow Compositions

### Workflow 1: Breadth-then-Depth
```
Quick mode (landscape scan)
  → identify top 3 gaps from critique
  → Deep mode on each gap
  → synthesize all into master report
```
**Uses:** Existing modes + `critique.py` gap extraction + new `research_chain` MCP tool.

### Workflow 2: Research-then-Monitor
```
Standard research → save report → schedule re-research
  → diff new vs old → alert on significant changes
```
**Uses:** `staleness.py` + `schema.py` + new `/research:monitor` skill.

### Workflow 3: Multi-Context Comparative
```
Same query × 3 context profiles → 3 reports
  → compare outputs → highlight perspective-dependent findings
```
**Uses:** Context system + new `/research:compare` skill.

### Workflow 4: Iterative Quality Loop
```
Standard research → critique → extract gaps → re-research gaps
  → merge findings → re-critique → repeat until avg score ≥ 4.0
```
**Uses:** `critique.py` + `iterate.py` + `schema.py` (partially built).

### Workflow 5: Evidence Chain (Extended Thinking)
```
Query → extended thinking decomposition → parallel sub-queries
  → evidence scoring per claim → chain-of-evidence report
```
**Uses:** Extended thinking API + `skeptic.py` + parallel synthesis.

---

## Cookbook Patterns Worth Adopting (Infrastructure)

| Pattern | Current State | Upgrade Path |
|---------|--------------|-------------|
| **Pydantic tool schemas** | Manual JSON in `mcp_server.py` | Auto-generate from Pydantic models with `Field` validators |
| **Context compaction** | Manual `token_budget.py` pruning | API-native `compaction_control` for long research sessions |
| **XML-structured LLM outputs** | Some XML usage | Standardize on XML tags for all LLM output parsing (more robust than regex on freeform text) |
| **Lazy tool loading** | All MCP tools loaded upfront | `describe_tool` meta-tool for future large tool sets |
| **PostToolUse hooks** | Not used | Audit trail for all research operations |
| **Safety boundaries** | SSRF + path traversal protection | Add command prefix validation, tool scoping per mode |

---

## Prioritized Implementation Order

### Tier 1 — High Impact, Low Effort (reuses existing infrastructure)
1. **`/research:compare`** — saved reports exist, comparing them is natural
2. **Reranking stage** — single additive module between relevance and synthesis, ~10% accuracy gain
3. **`verify_claim` MCP tool** — expose `skeptic.py` as standalone tool

### Tier 2 — High Impact, Medium Effort
4. **Breadth-then-depth workflow** — chains existing quick + deep modes
5. **`/research:briefing`** — map-reduce over saved reports
6. **`--verify` mode** — new frozen dataclass config, skeptic-first pipeline

### Tier 3 — Medium Impact, Higher Effort
7. **`/research:search-reports`** — requires embedding infrastructure
8. **`/research:monitor`** — requires persistent state management
9. **Context compaction** — API integration for long sessions
10. **`--exploration` mode** — new mode with broad search parameters

---

## Three Questions

1. **Hardest decision in this session?**
   Deciding which cookbook patterns are genuinely additive vs. which would introduce unnecessary complexity. The Skills system (`client.beta.skills.create()`) is interesting but doesn't map to Claude Code's markdown-based skill model. PTC is powerful but requires a code execution sandbox we don't have.

2. **What did you reject, and why?**
   - **PTC (Programmatic Tool Calling)**: Requires sandboxed code execution environment — too much infrastructure for the current CLI-based architecture.
   - **Pydantic schema auto-generation**: Nice-to-have but not a skill/workflow; it's plumbing. Deferred to a future refactor cycle.
   - **Custom MCP servers per domain**: The SRE agent pattern of domain-specific MCP servers is elegant but overkill when the existing `mcp_server.py` can grow incrementally.

3. **Least confident about going into the next phase?**
   Whether the embedding-based report search (`/research:search-reports`) justifies adding an embedding dependency (Voyage AI or similar) to a CLI tool that currently has zero vector infrastructure. It might be better served by simple keyword search + LLM reranking.
