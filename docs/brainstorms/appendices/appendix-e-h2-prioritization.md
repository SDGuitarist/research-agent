# Appendix E: H2 Prioritization — Dependency Graph, Impact, Alternative Orderings

**Source:** h2-priority agent, 2026-04-21
**Revised:** 2026-04-21 per Codex review (corrected dependency chain, fixed C34/C35 numbering)

## Real Dependency Graph (Verified Against Code)

```
C29 (evidence-tier labeling, skeptic enforcement, score-aware refinement)
 │
 └──> C32 (counter-search) — needs C29 skeptic severity markers to prioritize claims
       │
       └──> C33 (confidence scoring) — needs C32's CounterSearchResult.counter_evidence
             │
             ├──> C34 (research memory) — needs C33's ClaimConfidence tuples to store
             │                            structured knowledge (not raw text)
             │
             └──> C35 (adaptive planning) — needs C33's confidence_spread for assessment
                   │                         AND C34's prior knowledge for decisions
                   │
                   └── also overlaps iterate.py / coverage.py (not isolated)
```

**C32-35 form a real sequential dependency chain.** Each cycle's output feeds the next:

- C32 needs C29's skeptic severity markers to prioritize which claims to counter-search
- C33 needs C32's `CounterSearchResult` to populate `ClaimConfidence.counter_evidence`
- C34 needs C33's `ClaimConfidence` tuples to store structured knowledge (without them, stores raw text requiring later migration)
- C35 needs C33's `confidence_spread` for evidence assessment AND C34's prior knowledge entries for planning decisions
- C35 also overlaps existing `iterate.py` and `coverage.py` — both already do post-synthesis gap analysis and query refinement. C35 generalizes these, which means careful reconciliation, not a clean module addition.

## Impact Ranking

| Rank | Feature | Report Quality | Workflow Impact | Moat vs Google | Risk |
|------|---------|---------------|-----------------|----------------|------|
| 1 | **C34: Research Memory** | Medium-high | **Highest** | **Highest** (Google is stateless) | Medium-high |
| 2 | **C33: Confidence Scoring** | **Highest** | Medium | High | Medium |
| 3 | **C32: Counter-Search** | High | Low-medium | High | **Low** |
| 4 | **C35: Adaptive Planning** | Medium | Low | Medium (catch-up) | **Highest** |

## Alternative Orderings Considered

### Alternative A: Impact-First
C34 → C33 → C32 → C35
**Pro:** Highest-workflow-impact feature first. Every PFE run gets smarter.
**Con:** Memory stores unstructured data before C33; needs migration later. Breaks dependency chain.

### Alternative B: Low-Risk-First (CHOSEN)
C32 → C33 → C34 → C35
**Pro:** Quick win validates H2. C33 builds data model before persistence. No migration. Follows real dependency chain.
**Con:** Memory ships in C34 (third), not first.

### Final Decision: Dependency-Ordered
C32 → C33 → C34 → C35
**Rationale:** Counter-search first (quick win, low risk). Confidence scoring second (builds data model C34 needs). Memory third (stores structured data from day one). Adaptive planning last (highest risk, most internal, overlaps existing iterate/coverage, benefits from all prior).

## "Only Ship 2" Test

**Two different answers depending on the goal:**

**Moat pair: C32 (Counter-Search) + C33 (Confidence Scoring).** These are the capabilities no competitor has. Together they make every report adversarially verified and epistemically auditable. Best for differentiation. Follows the dependency chain (C32→C33).

**Workflow pair: C33 (Confidence Scoring) + C34 (Research Memory).** These create a compounding feedback loop:
1. Confidence-scored claims stored in memory
2. Next run queries memory for known facts
3. Agent focuses search on uncertain claims
4. Confidence scores improve over time

Best for the PFE competitive intelligence use case where the same topics are researched repeatedly.

**These are different decisions.** The moat pair maximizes differentiation; the workflow pair maximizes user value for repeat research. Both require C33 — it's the keystone.

**Implementation order for moat pair:** C32 first (counter-search), then C33 (confidence scoring).
**Implementation order for workflow pair:** C33 first (build data model), then C34 (persist it).
