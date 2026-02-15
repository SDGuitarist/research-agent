# Research Agent Integration Patterns

> Researched 2026-02-15 — How research agents are integrated into other apps and tools.

---

## 1. Integration Patterns

| Pattern | How It Works | Examples |
|---------|-------------|----------|
| **REST API** | HTTP endpoints, JSON responses | Tavily, Exa, Perplexity Sonar, You.com |
| **MCP Server** | Standardized protocol for LLM tool access | Exa MCP, Tavily MCP, GPT-Researcher MCP, Firecrawl, Jina Reader |
| **SDK/Framework** | Language-specific libraries | OpenAI Agents SDK, LangChain, Strands (AWS), Pydantic AI |
| **Embedded Library** | pip-installable, runs in-process | `gpt-researcher`, `knowledge-storm`, `strands-agents` |
| **Multi-Agent** | Specialized agent in a crew/swarm | CrewAI roles, AutoGen conversations, LangGraph nodes |
| **Workflow Automation** | No-code visual builders | Zapier Agents, n8n, Make.com |

---

## 2. Notable Open Source Projects

- **GPT-Researcher** (25.3k stars) — Planner-Executor-Publisher pattern, ~$0.40/deep research, outperformed Perplexity on benchmarks. Apache 2.0 license. Supports MCP integration for hybrid web + internal data research.
- **STORM** (Stanford) — 4-stage pipeline (knowledge curation, outline generation, article generation, polishing) generating Wikipedia-style articles with citations. Built on dspy. Install: `pip install knowledge-storm`.
- **LangChain Open Deep Research** — Simple, configurable, fully open-source. Achieved #6 on Deep Research Bench Leaderboard (score 0.4344). Works across many model providers, search tools, and MCP servers.
- **DeepResearchAgent** (SkyworkAI) — Hierarchical multi-agent system with top-level planning agent coordinating specialized lower-level agents. Added MCP support June 2025.
- **MiroThinker** — 80.8% Avg@8 on GAIA benchmark. Handles up to 400 tool calls per task.
- **Microsoft RD-Agent** — Automates R&D processes with AI-driven data and model enhancement.

---

## 3. Commercial API Pricing

| Service | Model | Price |
|---------|-------|-------|
| **Tavily** | Credit-based | $0.008/credit, research endpoint 15-250 credits/request |
| **Exa** | Per-search + per-page | $5/1k searches, $5-10/1k pages read |
| **Perplexity** | Tokens + requests | $1-15/1M tokens, $5-14/1k requests |
| **You.com** | Usage-based | ~$15/deep research call |

### Tavily
- Free tier: 1,000 credits/month
- Plans: $30/month (4,000 credits) to $500/month (100,000 credits)
- New `/research` endpoint (January 2026): fully managed multi-step workflow
- Models: "mini" (quick), "pro" (in-depth), "auto" (adaptive)

### Exa
- Async pipeline: `POST /research/v1`, poll for results
- exa-research: p50 45s, p90 90s
- exa-research-pro: 94.9% on SimpleQA benchmark
- Exa Instant (sub-200ms): $5/1k requests

### Perplexity
- OpenAI-compatible API format
- Models: Sonar, Sonar Pro, Sonar Deep Research, Sonar Reasoning Pro
- Citation tokens no longer billed for standard Sonar/Sonar Pro (2026)

### You.com
- Standard search: <445ms response time
- Deep Search: synthesizes hundreds of sources
- Free $100 credits for testing

---

## 4. MCP Server Implementations

MCP (Model Context Protocol), introduced by Anthropic November 2024, has become the standard for exposing research capabilities as discoverable, callable tools.

### Research Agent MCP Servers

- **GPT-Researcher MCP** (`gptr-mcp`) — Two-stage approach: smart tool selection then contextual research
- **Firecrawl MCP** — Scraping, crawling, mapping, structured extraction. Fastest MCP at 7s average, 83% accuracy
- **Jina AI Reader MCP** — URL-to-markdown, web search, image search, embeddings. Remote server at `https://mcp.jina.ai/v1`
- **MCP Omnisearch** — Unified access to Tavily, Brave, Kagi, Perplexity, FastGPT, Jina AI
- **Exa MCP** — Quick setup: `claude mcp add exa -e EXA_API_KEY=YOUR_KEY -- npx -y exa-mcp-server`

### MCP Tool Schema Example
```json
{
  "name": "web_search",
  "description": "Perform a semantic web search",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": { "type": "string" },
      "results": { "type": "number" }
    },
    "required": ["query"]
  }
}
```

### MCP Performance (2026)
- Bright Data: 100% success rate in web search & extraction
- Firecrawl: Fastest at 7 seconds average runtime
- Tool Search (Anthropic, January 2026): Reduces context consumption by up to 85%
- Adopted by OpenAI, Google DeepMind, Microsoft Copilot Studio

---

## 5. Agent Framework Integration

### LangChain/LangGraph

Two approaches to wrap research as a tool:

```python
# Decorator approach
from langchain.tools import tool

@tool
def research_web(query: str) -> str:
    """Performs deep web research on the given query."""
    return results

# BaseTool subclass
from langchain.tools import BaseTool

class ResearchTool(BaseTool):
    name = "research_web"
    description = "Performs deep web research"
    def _run(self, query: str) -> str:
        return results
```

LangGraph models agents as stateful graphs:
1. "agent" node calls LLM
2. If tool_calls present → route to "tools" node
3. "tools" node executes, returns ToolMessages
4. Loop until no tool_calls

### CrewAI — Role-Based

```python
from crewai import Agent, Task, Crew

research_agent = Agent(
    role='Research Analyst',
    goal='Conduct comprehensive research',
    tools=[tavily_tool, exa_tool],
    backstory='Expert researcher with web search access'
)

crew = Crew(agents=[research_agent], tasks=[task])
result = crew.kickoff()
```

### Multi-Agent Patterns

| Pattern | How It Works |
|---------|-------------|
| **Supervisor** | Main agent calls subagents as tools, synthesizes results |
| **Router** | Classifies input, directs to parallel specialized agents |
| **Planner/Task/Observer** | Planner generates approaches, Tasks execute, Observer maintains context |
| **Agent-as-Tool** | Wrap entire agent as a single callable tool for parent agent |

---

## 6. UI/UX Patterns

### Progress & Streaming
- Target time-to-first-token: under 800ms
- Show "thinking" indicators within 300ms
- SSE for one-way streaming, WebSocket for bidirectional

### Citations — Product Comparison

| Product | Citation Style |
|---------|---------------|
| **Perplexity** | Inline `[1]` `[2]` with source cards, hover previews |
| **ChatGPT Deep Research** | Document viewer with TOC left, footnotes right |
| **Gemini Deep Research** | Two-panel: conversation vs. research mechanics |
| **Manus** | Prominent research steps, automatic planning |

### Confidence Indicators
- High (>=85%): Green check
- Medium (60-84%): Yellow/orange caution
- Low (<60%): Red warning
- 70% of users found confidence ratings "very helpful" or "somewhat helpful"

### Research Triggers
- Natural language queries in chat
- Mode selectors (ChatGPT "agent mode", Perplexity "Deep Research")
- Dedicated buttons (Gemini "Deep Research" button)
- Slash commands
- Background execution with notifications (Gemini)
- Platform integration (Grok in X/Twitter)

### Output Formats
- Markdown reports (primary)
- Google Docs / PDF export (Gemini)
- Word documents (DeepResearchDocs.com)
- Slack messages (requires mrkdwn conversion)
- Email digests
- Interactive dashboards (Gemini Ultra)

---

## 7. SaaS Embedding

### CRM & Productivity

- **HubSpot Breeze** — Prospecting agent researches leads using full CRM context. Content, social media, and research agents.
- **Salesforce** — AI agents read data, write updates, trigger workflows. Gartner: 40% of enterprise apps will include task-specific AI agents by 2026.
- **Airtable Superagent** (Jan 2026) — Evaluates companies using FactSet, SEC filings, earnings transcripts, Crunchbase.
- **Notion AI** — Background agents run up to 20 minutes. Rebuilt with GPT-5 for autonomous workflows. MCP server available.
- **Slack** — Perplexity, ChatGPT, Claude integrated. Perplexity grounded in team conversations via MCP.
- **Glean** — 100+ app integrations, 30+ prebuilt agents, custom embedding models per customer.

### Workflow Automation

| Platform | Strengths | AI Capability |
|----------|-----------|---------------|
| **Zapier** | 8,000+ apps, simplest | Agents plan own steps, ~100 templates |
| **n8n** | Most advanced, self-hostable | 70 LangChain nodes, memory/chaining |
| **Make.com** | Visual builder, intermediate | Module Tools, reasoning panel |

---

## 8. Relevance to This Project

Our research agent already follows the dominant architecture (decompose → search → fetch → extract → summarize → synthesize). The main integration paths to consider:

1. **MCP Server** — Expose search/fetch/synthesize as MCP tools for Claude Code, Cursor, and other LLM clients. GPT-Researcher's MCP is a good reference implementation.
2. **REST API** — FastAPI wrapper for programmatic access. Follow Tavily/Exa patterns with async endpoints and polling for long-running research.
3. **Workflow Hooks** — Zapier/n8n integration via webhooks for scheduled or triggered research.
4. **CLI stays valuable** — GPT-Researcher's CLI is still their primary interface. Our CLI-first approach is aligned with the market.
5. **Embedded Library** — Package as pip-installable for other Python projects to import directly.

### Architecture Comparison

| Our Agent | GPT-Researcher | STORM | Exa Research |
|-----------|---------------|-------|-------------|
| decompose → search → fetch → cascade → extract → summarize → synthesize | plan → concurrent search/crawl → aggregate → report | curate → outline → generate → polish | decompose → parallel queries → structured JSON |
| Tavily + DuckDuckGo | Any search engine | You.com, Bing, Tavily, etc. | Proprietary neural search |
| Claude Sonnet | Any LLM | Any via dspy | Proprietary |
| CLI | CLI + Web UI + MCP | Python API | REST API |

---

## Sources

### Integration Patterns
- [APIs for AI Agents: 5 Integration Patterns (2026)](https://composio.dev/blog/apis-ai-agents-integration-patterns)
- [MCP Specification — Tools](https://modelcontextprotocol.io/specification/draft/server/tools)
- [MCP Benchmark: Top MCP Servers 2026](https://aimultiple.com/browser-mcp)

### APIs
- [Tavily Research API](https://docs.tavily.com/documentation/api-credits)
- [Exa Research API](https://docs.exa.ai/reference/exa-research)
- [Perplexity API](https://docs.perplexity.ai/docs/getting-started/pricing)
- [You.com APIs](https://you.com/apis)

### Open Source
- [GPT-Researcher](https://github.com/assafelovic/gpt-researcher)
- [STORM (Stanford)](https://github.com/stanford-oval/storm)
- [LangChain Open Deep Research](https://github.com/langchain-ai/open_deep_research)
- [DeepResearchAgent](https://github.com/SkyworkAI/DeepResearchAgent)

### Frameworks
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)
- [LangGraph Multi-Agent](https://blog.langchain.com/langgraph-multi-agent-workflows/)
- [CrewAI](https://www.crewai.com/)
- [Strands Agents SDK (AWS)](https://aws.amazon.com/blogs/machine-learning/build-dynamic-web-research-agents-with-the-strands-agents-sdk-and-tavily/)

### UI/UX
- [Deep Research UIs Comparison](https://www.franciscomoretti.com/blog/comparing-deep-research-uis)
- [AI UX Patterns — Citations](https://www.shapeof.ai/patterns/citations)
- [Confidence Visualization Patterns](https://agentic-design.ai/patterns/ui-ux-patterns/confidence-visualization-patterns)

### SaaS Embedding
- [HubSpot Breeze AI](https://www.hubspot.com/products/artificial-intelligence)
- [Notion Agent Architecture](https://www.rdj.ai/understanding-notion-s-custom-ai-agent-architecture)
- [Airtable Superagent](https://techcrunch.com/2026/01/27/airtables-valuation-fell-by-7-million-its-founder-thinks-that-was-just-the-warm-up/)

### Workflow Automation
- [Zapier Agents](https://zapier.com/agents)
- [n8n AI Agents](https://n8n.io/ai-agents/)
- [Make.com AI Agents](https://www.make.com/en/ai-agents)
