# Research Agent Features, Tools & Abilities (2025-2026)

**Date**: 2026-02-15
**Method**: Four parallel research agents covering architectures, search tools, output/synthesis, and advanced abilities

---

## 1. Architectures & Core Patterns

| Pattern | Description | Used By |
|---|---|---|
| **ReAct** | Thought→Action→Observation loop | Claude Code, simple agents |
| **Plan-and-Execute** | Explicit plan first, then execute steps | Perplexity, Gemini, GPT-Researcher |
| **Tree-of-Thought** | Branch/evaluate/backtrack multiple reasoning paths | Complex problem-solving |
| **Reflexion** | Self-critique stored in episodic memory for improvement | LangChain Open Deep Research |
| **Agentic RAG** | Agent-driven retrieval that evaluates and iterates | Replacing static RAG everywhere |

### Multi-Agent Coordination (72% of enterprise AI projects)

- **Supervisor/Manager**: Central agent delegates to specialists (GPT-Researcher's Chief Editor)
- **Handoff**: Agents transfer execution to more suitable agents (OpenAI Agents SDK)
- **Swarm**: Self-organizing dynamic teams (AutoGen, Microsoft Agent Framework)
- **Debate/Adversarial**: Multiple agents argue positions or review each other's work (STORM)
- **Ensemble/Routing**: Model routing selects best LLM per sub-task (Perplexity Comet)

### Memory Architectures

- **Short-term**: Context window (all agents)
- **Episodic**: Records of specific events/interactions for future improvement (Reflexion)
- **Semantic**: General knowledge via RAG with vector embeddings
- **Procedural**: Workflows and successful strategies (least commonly implemented)
- **Mem0**: Production memory layer with graph-based storage, 26% improvement over OpenAI's memory, 90%+ token cost savings

### Reference Architectures

| System | Architecture | Decomposition | Orchestration | Coordination |
|---|---|---|---|---|
| **OpenAI Deep Research** | Plan-and-execute + multi-agent pipeline | Triage→Clarify→Instruct→Research | Sequential + parallel search | Handoff (Agents SDK) |
| **Gemini Deep Research** | Plan-and-execute + async task manager | Planning stage breaks into sub-tasks | Parallel + sequential (auto-chosen) | Single-agent with self-critique |
| **Perplexity Pro** | Plan-and-execute + model routing | Step-by-step plan generation | Sequential steps, parallel queries | Ensemble (retrieval + synthesis + verification) |
| **GPT-Researcher** | Hierarchical multi-agent | Editor plans outline, sections become tasks | Parallel section research | Supervisor (Chief Editor) |
| **STORM (Stanford)** | Perspective-guided conversation | Discover perspectives from related articles | Sequential conversations, parallel perspectives | Simulated expert debate |
| **LangChain Open Deep Research** | Supervisor-researcher with reflection | Section-by-section planning | Parallel section writing | Supervisor spawns sub-agents |

---

## 2. Search & Retrieval Tools

### AI-Native Search APIs

| Tool | Strength | Weakness | Pricing |
|---|---|---|---|
| **Tavily** | LLM-ready output, LangChain/LlamaIndex native | Higher per-query cost at scale | 1K free credits/mo, credit-based |
| **Exa** | Deep semantic understanding, "next-link prediction" | Higher cost, smaller index | Commercial |
| **Perplexity Sonar** | Citation quality, conversational answers | Unpredictable per-query costs | $5/1K requests + tokens |
| **Linkup** | 91% F-Score (beat Sonar), GDPR, flat pricing | Less brand recognition | ~65% cheaper than Perplexity |

### Traditional SERP APIs

| Tool | Strength | Weakness | Pricing |
|---|---|---|---|
| **Brave Search** | Independent 35B page index, privacy-first | Smaller index than Google, no free tier | $3-5/1K searches |
| **Serper** | Cheap, reliable Google results | Dependent on Google infrastructure | $0.30-2.00/1K requests |
| **SerpAPI** | Multi-engine support, enterprise reliability | Highest cost in category | $75/mo for 5K searches |

**Best practice**: "Use Serper for volume, Tavily for quality, Perplexity for speed, Exa for research." Most production agents use primary + fallback (e.g., Tavily + DuckDuckGo/Brave).

### Web Scraping & Content Extraction

| Tool | Type | Best For |
|---|---|---|
| **Firecrawl** | Managed API | Structured extraction with natural language prompts |
| **Jina Reader** | Managed API | Simple page extraction, prototyping |
| **Crawl4AI** | Open-source | Self-hosted, offline, data sovereignty |
| **trafilatura** | Python library | Boilerplate removal, fallback layer |
| **Playwright** | Browser automation | JS-rendered pages, authentication flows |

**Recommended hybrid pattern** (URL triage by type):
- Simple content pages → Jina Reader
- Documentation sites → Crawl4AI
- Bulk sitemaps → Spider
- Social media → Apify Actors
- Complex authentication → Playwright

### Academic & Scholarly Search

| Tool | Coverage | API | Best For |
|---|---|---|---|
| **Semantic Scholar** | 200M+ papers | Free API | AI-enhanced discovery, primary academic backend |
| **Google Scholar** | Broadest coverage | No official API (scraping required) | Breadth |
| **PubMed** | Biomedical | Entrez/E-utilities API | Biomedical research |
| **arXiv** | CS, physics, math preprints | API available | Preprints |

### PDF Parsing (2025 Benchmark of 17 parsers)

| Tool | Type | Strength |
|---|---|---|
| **LlamaParse** | Commercial | Robustness leader (81% ChrF++) |
| **MinerU** | Open-source | Best all-rounder, multi-language |
| **Docling (IBM)** | Open-source | 97.9% accuracy on complex tables |
| **Reducto** | Commercial | "Agentic OCR" with self-correction |

---

## 3. RAG Patterns

| Pattern | Description | Best For |
|---|---|---|
| **Naive/Basic RAG** | Query→vector search→top-k→generate | Simple factual Q&A |
| **Corrective RAG (CRAG)** | Evaluates relevance, rewrites queries on failure | Improving retrieval quality |
| **Self-RAG** | Iterative self-evaluation + retrieval adjustment | High-accuracy requirements |
| **Adaptive RAG** | Routes queries to different strategies by complexity | Cost optimization |
| **Agentic RAG** | Autonomous agents control entire retrieval pipeline | Complex multi-step research |
| **Graph RAG** | Knowledge graphs for multi-hop reasoning | Relationship-heavy queries |

**Current best practice**: Adaptive RAG (route by complexity) + Corrective RAG (self-grade + fallback) via LangGraph.

---

## 4. Output Generation & Synthesis

### Report Formats

- **Markdown**: Universal across all systems
- **PDF/DOCX**: GPT-Researcher (Publisher agent), OpenAI Deep Research (one-click export)
- **Structured data**: Elicit (structured tables from papers, 99.4% accuracy), GPT-Researcher (JSON/CSV)
- **Interactive visuals**: Google Gemini Visual Reports only (charts, simulations, concept maps, quizzes)

### Citation Approaches

| System | Style | Accuracy |
|---|---|---|
| **Google Deep Research** | Numbered inline + Works Cited | Not independently measured |
| **OpenAI Deep Research** | Numbered + source list + document viewer | Not independently measured |
| **Perplexity** | Numbered + hover + confidence grades | 78% claims tied to sources (best) |
| **STORM** | Wikipedia-style references | Claims 99% factual accuracy |

**Key finding**: Citation error rates remain ~37%+ across all systems (Columbia Tow Center study, March 2025).

### Synthesis Techniques

- **Multi-document summarization**: OpenAI analyzes hundreds of sources; GPT-Researcher aggregates 20+ per query
- **Multi-perspective questioning**: STORM simulates conversations from different perspectives
- **Claim extraction**: Elicit extracts structured data points (1,502/1,511 correct in Cochrane comparison)
- **Contradiction detection**: Only FutureHouse Falcon explicitly detects conflicts across sources
- **Outline-first**: STORM, Google, GPT-Researcher all generate outlines before writing

### Quality Control

- **Self-reflection**: Reviewer + Reviser agents (GPT-Researcher), multi-perspective (STORM)
- **Verification loops**: FutureHouse Robin does end-to-end experimental validation
- **Confidence scoring**: Perplexity grades sources as high/medium/uncertain
- **Limitation**: Agents judging their own work cannot guarantee truth without external grounding

### Iterative Refinement

- **Co-STORM**: Human-AI collaborative curation through roundtable conversation
- **GPT-Researcher Deep Mode**: Tree-like recursive exploration of subtopics
- **OpenAI Deep Research**: 5-30 minute autonomous web navigation with dynamic plan adjustment

---

## 5. Advanced & Differentiating Abilities

### Reasoning

- **Test-time compute scaling** often beats bigger models (UC Berkeley, ICLR 2025 Oral)
- **Process Reward Models (PRMs)** score each intermediate reasoning step
- **DeepSeek-R1**: Pure RL produced reasoning matching o1 (AIME: 15.6% → 71%)
- **o3-mini**: Parity with o1 at 15x lower cost, 5x faster

### Real-Time Data

- **MCP (Model Context Protocol)**: Anthropic's open standard for plug-and-play tool connectivity
- **A2A (Agent-to-Agent)**: Google's cross-vendor agent communication protocol
- **Hybrid approach**: Change Data Capture for speed-critical data, scheduled updates elsewhere
- Perplexity processes 200M daily queries at 358ms median latency

### Tool Use Beyond Search

- **Code execution**: Sandboxed Python (OpenAI, Claude, Gemini)
- **Browser automation**: OpenAI Operator (58% success on WebVoyager), Skyvern, Browser Use
- **Multi-tool chains**: OpenAI Deep Research reads HTML, parses PDFs, analyzes chart images, runs code in one session

### Multimodal Research

- **OpenAI Deep Research**: Analyzes PDFs, chart images, and text together
- **Gemini 2.5 Pro**: 1M+ token context, text/image/audio/video input
- **Microsoft MMCTAgent**: Multimodal reasoning over large video/image collections
- Gartner: 40% of GenAI solutions multimodal by 2027 (up from 1% in 2023)

### Prompt Injection Defense

- **Multi-layered defense** (content filtering + embedding anomaly detection + hierarchical guardrails + multi-stage verification) reduced attack success from 73.2% to 8.7%
- OpenAI says deterministic defense is impossible
- **"Lethal Trifecta"**: Systems most vulnerable when they have (1) private data access, (2) untrusted token exposure, (3) exfiltration vectors
- Best current approach: content sanitization + XML boundaries + system prompt guardrails + output verification

### Cost Optimization

| Strategy | Savings |
|---|---|
| **Prompt caching** | 75% cheaper on cached tokens, 42% monthly reduction |
| **Model cascading** | 60%+ (cheap models for routing, expensive for reasoning) |
| **Batch processing** | 50% discount for async |
| **RAG over full-context** | Pay tokens only for relevant chunks |
| **Context window management** | 20-40% reduction in multi-turn apps |

---

## 6. Emerging Trends for 2026

1. **Agentic RAG** replaces static retrieve-then-generate with autonomous, self-correcting retrieval loops
2. **GraphRAG** combines vector search with knowledge graphs for structured reasoning (99% search precision in some systems)
3. **Multi-agent teams** over monolithic agents — specialized retriever/synthesizer/verifier roles
4. **Hybrid neural-symbolic systems** blend LLM creativity with domain-specific logic for governance and explainability
5. **Memory as infrastructure** — Mem0, AWS AgentCore, LangGraph+MongoDB as first production-grade persistent memory
6. **Test-time reasoning** — allocate more compute at inference for harder problems instead of scaling model size
7. **Open-source competitiveness** — GPT Researcher and Tongyi DeepResearch match commercial offerings on academic benchmarks

---

## 7. Commercial Deep Research Comparison

| Feature | OpenAI Deep Research | Google Gemini Deep Research | Perplexity Deep Research |
|---|---|---|---|
| **Model** | o3/o4-mini (reasoning-optimized) | Gemini 2.5 Pro | Multi-model routing (GPT-5, Claude 4.5, Mistral) |
| **Approach** | Agentic (dynamic pivoting) | Structured plan (user-reviewable) | Iterative search + reasoning |
| **Multimodal** | Text, images, PDFs | Text only | Text primarily |
| **Speed** | 5-30 minutes | 5-15 minutes | 2-4 minutes |
| **Sources/query** | Hundreds | Hundreds | 300+ (Pro Search) |
| **Cost** | $200/mo (Pro), $20/mo (Plus, limited) | $20/mo | $20/mo (Pro) |
| **Strength** | Deepest reasoning, multimodal | Speed, user control over plan | Speed, citation quality, API |

---

## Sources

### Architecture & Patterns
- [Agentic AI: Architectures, Taxonomies (arXiv:2601.12560)](https://arxiv.org/pdf/2601.12560)
- [OpenAI Deep Research Architecture](https://cobusgreyling.medium.com/openai-deep-research-ai-agent-architecture-7ac52b5f6a01)
- [Deep Research API with Agents SDK](https://cookbook.openai.com/examples/deep_research_api/introduction_to_deep_research_api_agents)
- [Gemini Deep Research](https://ai.google.dev/gemini-api/docs/deep-research)
- [GPT-Researcher GitHub](https://github.com/assafelovic/gpt-researcher)
- [STORM Stanford](https://storm-project.stanford.edu/research/storm/)
- [LangChain Open Deep Research](https://github.com/langchain-ai/open_deep_research)
- [Reflexion (NeurIPS 2023)](https://arxiv.org/abs/2303.11366)
- [Agentic RAG Survey (arXiv:2501.09136)](https://arxiv.org/abs/2501.09136)
- [Mem0 Paper (arXiv:2504.19413)](https://arxiv.org/abs/2504.19413)
- [Multi-Agent Coordination Survey (arXiv:2502.14743)](https://arxiv.org/html/2502.14743v2)

### Search & Retrieval
- [Tavily Official](https://www.tavily.com/)
- [Exa API 2.0](https://exa.ai/blog/exa-api-2-0)
- [Perplexity Sonar API](https://www.perplexity.ai/hub/blog/introducing-the-sonar-pro-api)
- [Brave Search API](https://brave.com/search/api/)
- [Firecrawl](https://www.firecrawl.dev/)
- [Crawl4AI Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
- [PDF Benchmark 2025](https://procycons.com/en/blogs/pdf-data-extraction-benchmark/)
- [Semantic Scholar](https://www.semanticscholar.org/)

### Output & Synthesis
- [Google Visual Reports](https://blog.google/products/gemini/visual-reports/)
- [Perplexity Accuracy Tests 2025](https://skywork.ai/blog/news/perplexity-accuracy-tests-2025-sources-citations/)
- [Elicit Data Extraction Study (Cochrane)](https://onlinelibrary.wiley.com/doi/full/10.1002/cesm.70033)
- [FutureHouse Platform](https://www.futurehouse.org/research-announcements/launching-futurehouse-platform-ai-agents)
- [PaperQA2: Superhuman Synthesis](https://arxiv.org/pdf/2409.13740)
- [Deep Research Survey (arXiv:2508.12752)](https://arxiv.org/abs/2508.12752)

### Advanced Abilities
- [Test-Time Compute Scaling (ICLR 2025)](https://openreview.net/forum?id=4FWAwZtd2n)
- [OpenAI: Introducing Operator](https://openai.com/index/introducing-operator/)
- [OpenAI: Why LLMs Hallucinate](https://openai.com/index/why-language-models-hallucinate/)
- [OpenAI: Prompt Injections](https://openai.com/index/prompt-injections/)
- [Prompt Injection Defense (MDPI)](https://www.mdpi.com/2078-2489/17/1/54)
- [Securing AI Agents (arXiv:2511.15759)](https://arxiv.org/abs/2511.15759)
- [AI Trends 2026: Reflective Agents (HuggingFace)](https://huggingface.co/blog/aufklarer/ai-trends-2026-test-time-reasoning-reflective-agen)
