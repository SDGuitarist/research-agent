# Best Practices for Building Research Agents

**Research Date:** 2026-02-05
**Purpose:** Inform Cycle 7 planning for the research agent

---

## 1. Search Quality for Niche Topics

### How Leading Projects Handle Source Quality

#### GPT Researcher Architecture

[GPT Researcher](https://github.com/assafelovic/gpt-researcher) uses a **hybrid multi-retriever strategy** combining multiple search providers:

```python
# Hybrid strategy: combines web search with specialized sources
os.environ["RETRIEVER"] = "tavily,mcp"

# For academic research, combine multiple specialized retrievers
os.environ["RETRIEVER"] = "arxiv,semantic_scholar,mcp"
```

Key patterns:
- **Parallel research subgraphs** with researcher -> reviewer -> reviser cycles
- **Multi-agent workflow** using LangGraph for coordinated research
- **Configurable retriever chains** combining web search with domain-specific sources

#### Stanford STORM's Multi-Perspective Approach

[STORM](https://storm-project.stanford.edu/research/storm/) from Stanford OVAL:

1. **Perspective-Guided Question Asking**: Discovers diverse perspectives by surveying existing articles
2. **Simulated Conversations**: Models conversations between writer and expert grounded in sources
3. **Multi-hop Retrieval**: Updates understanding and asks follow-up questions

The 2024 update introduced **Co-STORM** for human-AI collaboration and **VectorRM** for user-provided documents.

#### Perplexity AI's Architecture

From [Perplexity's research docs](https://research.perplexity.ai/articles/architecting-and-evaluating-an-ai-first-search-api):

- **Hybrid retrieval**: Lexical and semantic queries merged into hybrid candidate set
- **Multi-stage reranking**: Fast lexical/embedding scorers → powerful cross-encoder rerankers
- **Sub-document level retrieval**: Atomic units for precise context
- **Intelligent routing**: Classifier models determine query complexity

### Recommendations for Niche Topics

1. **Use multiple specialized retrievers** rather than general web search alone
2. **Implement perspective diversification** to avoid mainstream bias
3. **Add domain-specific sources** (academic databases, specialized APIs, curated collections)
4. **Use semantic search** for conceptual relationships, not just keywords

---

## 2. Search Provider Strategies

### Provider Comparison Matrix (2025-2026)

| Provider | Best For | Cost (per 1K) | Strengths | Limitations |
|----------|----------|---------------|-----------|-------------|
| **Tavily** | AI agents, RAG | $8 | Source-first, citation-optimized | Web only |
| **Exa** | Semantic/neural | $5 | Neural embeddings, conceptual | Smaller index |
| **Brave** | Privacy apps | Competitive | Independent index, fast, private | Less comprehensive |
| **Serper** | Budget/volume | $0.30-$1.00 | Fastest, cheapest, Google results | Google only |
| **SerpAPI** | Multi-engine | $8-$15 | 20+ engines, comprehensive | Higher cost |
| **Google CSE** | Google-specific | $5 | Official Google results | 10K/day limit |

**CRITICAL: Bing Search API retired August 11, 2025.** Microsoft replacement costs $35/1K queries.

Sources: [Firecrawl Guide](https://www.firecrawl.dev/blog/top_web_search_api_2025), [DEV.to Comparison](https://dev.to/ritza/best-serp-api-comparison-2025)

### Provider Selection by Use Case

**For AI Agents (recommended stack):**
```python
# Primary: Tavily (optimized for LLM context)
# Secondary: Exa (semantic search for conceptual queries)
# Tertiary: Serper (high-volume, budget-friendly fallback)
```

**For Academic/Research:**
```python
# Primary: Semantic Scholar API
# Secondary: arXiv API
# Tertiary: Tavily for web context
```

### Multi-Provider Fallback Strategies

Based on [Portkey](https://portkey.ai/docs/product/ai-gateway/fallbacks) and [API7.ai](https://api7.ai/blog/fallback-api-resilience-design-patterns):

```python
SEARCH_PROVIDERS = [
    {"provider": "tavily", "priority": 1, "timeout": 5000},
    {"provider": "exa", "priority": 2, "timeout": 5000},
    {"provider": "serper", "priority": 3, "timeout": 3000},
]

# Key resilience patterns:
# 1. Circuit breakers - stop requests to failing services
# 2. Bulkheads - isolate failing components
# 3. Timeouts - prevent hanging requests
# 4. Retry with exponential backoff
# 5. Rate limiting per provider
```

**Benefits:**
- Automatic rerouting during outages
- Cost optimization by query type routing
- Quality optimization using best provider per domain

---

## 3. Common Pitfalls in Research/RAG Tools

### Source Quality Issues

[Stanford legal RAG research](https://dho.stanford.edu/wp-content/uploads/Legal_RAG_Hallucinations.pdf) found even domain-specific tools produced hallucinations in **17-34% of cases**:
- Mis-citing sources
- Agreeing with incorrect user premises

**Mitigation:**
1. Implement source verification pipelines
2. Use reranking to prioritize authoritative sources
3. Cross-reference multiple sources before including
4. Audit vector indexes regularly

### Hallucination Problems

From [academic research](https://arxiv.org/html/2510.24476v1):

**Root causes:**
1. **Temporal misalignment**: Pre-training outdated, context current
2. **Misinformation pollution**: Retrieved content contains errors
3. **Knowledge conflict**: Retrieved content conflicts with parametric knowledge
4. **Knowledge FFN overemphasis**: Models prioritize parametric over retrieved

**Key finding (2025):** Up to **57% of citations lack faithfulness despite potential correctness**. Both correctness AND faithfulness must be evaluated.

[CiteGuard framework](https://kathcym.github.io/CiteGuard_Page/) achieved 12.3% accuracy improvement using retrieval-augmented validation.

### Context Window Management

From [RAGFlow 2025 review](https://www.ragflow.io/blog/rag-review-2025-from-rag-to-context):

**"Lost in the Middle" Problem:** Stuffing lengthy text scatters model attention, degrading quality.

**Chunking Benchmarks (2024):**

| Strategy | Accuracy | Best For |
|----------|----------|----------|
| Page-level | 0.648 | Consistent performance |
| Semantic | Variable | Topic-based retrieval |
| 256-512 tokens | High | Factoid queries |
| 1024+ tokens | High | Analytical queries |

**Recommended approach:**
```python
chunk_size = 400-512  # tokens
overlap = 0.10-0.20   # 10-20%

# Enrich chunks with document-level context after segmentation
# Limit chunk count - too many saturates context
```

### Over-Reliance on Single Search Passes

From [LevelRAG](https://arxiv.org/html/2502.18139v1) and [adaptive RAG studies](https://www.sciencedirect.com/science/article/pii/S0925231225029443):

**Problem:** Single-step retrieval misses complex relationships and multi-hop reasoning.

**Solution - Iterative Retrieval:**
```python
for iteration in range(max_iterations):
    # 1. Process query
    # 2. Retrieve evidence
    # 3. Reflect on completeness
    # 4. Refine query if needed
    # 5. Continue until sufficient coverage
```

**Advanced patterns:**
- **IM-RAG**: Inner monologue alternating generation and retrieval
- **GenGround**: Generate provisional answer, then retrieve evidence
- **SelfRAG**: Adaptive retrieval based on reflection tokens
- **RQ-RAG**: Query decomposition for multi-hop QA

---

## 4. Handling Comparison Queries ("X vs Y")

### Query Decomposition Strategies

From [Deep Research survey](https://arxiv.org/html/2508.12752v1) and [WebThinker](https://arxiv.org/pdf/2408.08435):

**Multi-agent architecture:**
```python
agents = {
    "planner": "Task decomposition and subgoal scheduling",
    "query_agent": "Generating diversified and contextual queries",
    "retriever": "Evidence gathering from external tools",
    "writer": "Structured synthesis",
}

# Section-aware decomposition enables parallel research
```

### Ensuring Balanced Coverage

**STORM's approach:**
1. Discover diverse perspectives by surveying existing articles
2. Use perspectives to control question-asking
3. Simulate conversations from multiple viewpoints

**Diverge framework** ([recent research](https://arxiv.org/html/2602.00238)):
- Explicit reflection on uncovered viewpoints
- Long-horizon diversity preservation
- Iterative RAG with lightweight memory
- Evidence-grounded generation

### Avoiding Bias Toward Popular Options

**Strategies:**
1. **Explicit perspective enumeration**: Enumerate all perspectives before searching
2. **Balanced query generation**: Equal queries for each side
3. **Source diversity requirements**: Minimum sources per perspective
4. **Popularity-aware reranking**: De-weight sources that only discuss popular option

**Implementation pattern:**
```python
def handle_comparison_query(query: str):
    # 1. Parse comparison targets
    targets = extract_comparison_targets(query)  # ["X", "Y"]

    # 2. Generate balanced sub-queries
    sub_queries = []
    for target in targets:
        sub_queries.extend([
            f"advantages of {target}",
            f"disadvantages of {target}",
            f"use cases for {target}",
            f"limitations of {target}",
        ])

    # 3. Ensure balanced retrieval
    results_per_target = {}
    for target in targets:
        results_per_target[target] = retrieve_with_minimum(
            queries=[q for q in sub_queries if target in q],
            min_sources=5,
            min_perspectives=3
        )

    # 4. Synthesize with balance check
    return synthesize_comparison(
        results_per_target,
        require_balanced_coverage=True
    )
```

### Comparison Query Checklist

- [ ] Explicitly identify all comparison targets
- [ ] Generate queries for each target independently
- [ ] Set minimum source thresholds per target
- [ ] Include both advantages AND disadvantages
- [ ] Cross-reference claims between sources
- [ ] Flag significantly unbalanced coverage
- [ ] Consider recency - newer options may have less coverage

---

## 5. Key Recommendations Summary

### Architecture

1. Use **multi-agent workflows** with specialized roles
2. Implement **iterative retrieval** with reflection cycles
3. Add **review-revise loops** for quality control

### Search Strategy

| Priority | Provider | Use Case |
|----------|----------|----------|
| Primary | Tavily or Exa | AI-optimized search |
| Fallback | Serper | High-volume/budget |
| Specialized | arXiv, Semantic Scholar | Academic content |
| Avoid | Bing API (deprecated) | - |

### Quality Control

1. Implement **citation verification** pipelines
2. Match **chunking strategy** to query type
3. Avoid **context window saturation**
4. Distinguish citation **correctness** from **faithfulness**

### Comparison Queries

1. **Decompose** into balanced sub-queries per target
2. **Enumerate perspectives** explicitly before searching
3. Set **minimum coverage thresholds** per side
4. Use **diversity-preserving** retrieval

---

## Sources

### Official Documentation
- [GPT Researcher](https://github.com/assafelovic/gpt-researcher)
- [Stanford STORM](https://storm-project.stanford.edu/research/storm/)
- [Perplexity Architecture](https://research.perplexity.ai/articles/architecting-and-evaluating-an-ai-first-search-api)

### Search Providers
- [Tavily](https://tavily.com/)
- [Exa AI](https://docs.exa.ai/reference/how-exa-search-works)
- [Brave Search API](https://brave.com/search/api/)
- [Serper](https://serper.dev/)

### Research Papers
- [CiteGuard](https://kathcym.github.io/CiteGuard_Page/)
- [RAG Hallucinations Survey](https://arxiv.org/html/2510.24476v1)
- [Deep Research Survey](https://arxiv.org/html/2508.12752v1)
- [Chunking Strategies 2025](https://www.firecrawl.dev/blog/best-chunking-strategies-rag-2025)
- [RAG to Context 2025](https://www.ragflow.io/blog/rag-review-2025-from-rag-to-context)

### Comparisons
- [AI Search APIs 2025](https://www.firecrawl.dev/blog/top_web_search_api_2025)
- [SERP API Comparison](https://dev.to/ritza/best-serp-api-comparison-2025)
- [Bing API Retirement](https://www.valyu.ai/blogs/bing-search-api-is-dead-now-what)
