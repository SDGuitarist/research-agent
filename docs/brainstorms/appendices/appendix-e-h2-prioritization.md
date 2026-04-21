# Appendix E: H2 Prioritization — Dependency Graph, Impact, Alternative Orderings

**Source:** h2-priority agent, 2026-04-21

## Real Dependency Graph (Proven by Code)

```
C29 (evidence-tier labeling, skeptic enforcement, score-aware refinement)
 |
 ├──> C32 (counter-search) — needs skeptic enforcement from C29
 |
 ├──> C33 (confidence scoring) — needs evidence-tier labels from C29
 |
 └──> C34 (adaptive planning) — benefits from C29 score-aware refinement
       |
       └──(benefits from)──> C33 (confidence data improves planning decisions)

C35 (research memory) — independent of C32, C33, C34
  └──(benefits from)──> C33 (structured claims are better to store than raw text)
```

**Key finding: C32, C33, C34, and C35 are mostly independent of each other.** They all depend on C29, not on each other. The brainstorm's original linear chain was assumed, not real.

**One real intra-H2 dependency:** C34 (adaptive planning) benefits materially from C33 (confidence data). C35 (memory) benefits from C33 (structured claims to store).

## Impact Ranking

| Rank | Feature | Report Quality | Workflow Impact | Moat vs Google | Risk |
|------|---------|---------------|-----------------|----------------|------|
| 1 | **C35: Research Memory** | Medium-high | **Highest** | **Highest** (Google is stateless) | Medium-high |
| 2 | **C33: Confidence Scoring** | **Highest** | Medium | High | Medium |
| 3 | **C32: Counter-Search** | High | Low-medium | High | **Low** |
| 4 | **C34: Adaptive Planning** | Medium | Low | Medium (catch-up) | **Highest** |

## Alternative Orderings Considered

### Alternative A: Impact-First
C35 → C33 → C32 → C34
**Pro:** Highest-workflow-impact feature first. Every PFE run gets smarter.
**Con:** Memory stores unstructured data before C33; needs migration later.

### Alternative B: Low-Risk-First (CHOSEN, modified)
C32 → C33 → C34 → C35
**Pro:** Quick win validates H2. C33 builds data model before persistence. No migration.
**Con:** Memory ships later (C34 instead of C32).

### Final Decision: Modified Low-Risk-First
C32 → C33 → C34(memory) → C35(planning)
**Rationale:** Counter-search first (quick win, low risk). Confidence scoring second (data model). Memory third (stores structured data from day one). Adaptive planning last (highest risk, most internal, benefits from all prior).

## "Only Ship 2" Test

**Ship C33 (Confidence Scoring) + C35 (Research Memory).**

Together they create a compounding feedback loop:
1. Confidence-scored claims stored in memory
2. Next run queries memory for known facts
3. Agent focuses search on uncertain claims
4. Confidence scores improve over time

Neither C32 nor C34 creates this self-reinforcing cycle.

**Implementation order if only 2:** C33 first (build data model), then C35 (persist it). Avoids migration cost.
