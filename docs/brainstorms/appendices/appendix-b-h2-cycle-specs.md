# Appendix B: H2 Detailed Cycle Specs (C32-35)

**Source:** h2-scoping agent, 2026-04-21
**Format:** Matches entropy roadmap depth (docs/research/2026-03-09-entropy-fixes-roadmap.md)

## Design Principles (Extending from Epistemic Calibration Study)

4. **Adversarial search before confidence scoring** — you cannot confidently score a claim until you have actively looked for evidence against it.
5. **Structured data before adaptive logic** — adaptive re-planning needs quantitative signals (score distributions, confidence spreads).
6. **Persistent memory last** — a knowledge graph is only as good as the data flowing into it.

---

## Cycle 32: Adversarial Counter-Search (5 sessions, ~245 lines, confidence 80%)

**Theme:** After drafting, actively search for evidence that contradicts each major claim.

| # | Item | Module | What Changes | Est. Size |
|---|------|--------|-------------|-----------|
| H2-1 | Extract claims from draft | `skeptic.py` | New `extract_claims()` async function | ~50 lines |
| H2-2 | Generate counter-queries | `skeptic.py` | New `generate_counter_queries()` — negation-framed searches | ~40 lines |
| H2-3 | Counter-search pipeline | `agent.py` | New `_run_counter_search()` — reuses existing search/fetch/summarize infra | ~80 lines |
| H2-4 | Counter-evidence in synthesis | `synthesize.py` | New `<counter_evidence>` XML block, `[Disputed]` markers | ~40 lines |
| H2-5 | CounterSearchResult data model | `skeptic.py` | Frozen dataclass: claim, counter_query, counter_summaries, has_disconfirmation | ~20 lines |
| H2-6 | Mode gating | `modes.py`, `agent.py` | `counter_search: bool` field — False/quick, True/standard+deep | ~15 lines |

**Dependencies:** C29 skeptic enforcement (severity signal for prioritization), C29 evidence-tier labeling (focus counter-search on documented claims).

**Design notes:**
- Confidence 80%. Counter-query phrasing needs A/B testing (negation vs alternative-framing).
- Reuses `_search_sub_queries()` and `_fetch_extract_summarize()` — no new search infrastructure.
- Cost impact: ~$0.15-$0.30/standard run, ~$0.25-$0.50/deep.
- Standard mode: counter-search top 3 claims by skeptic severity. Deep mode: all claims.

**Acceptance criteria (EARS):**
- WHEN standard mode completes draft THE SYSTEM SHALL extract 3-5 major factual claims
- WHEN counter-search finds credible disconfirmation THE SYSTEM SHALL mark claim as `[Disputed]` with both sides presented
- WHEN counter-search finds nothing THE SYSTEM SHALL not modify the claim
- WHEN mode is quick THE SYSTEM SHALL skip counter-search entirely
- WHEN counter-search API calls fail THE SYSTEM SHALL continue with available evidence (graceful degradation)

---

## Cycle 33: Epistemic Confidence Scoring (6 sessions, ~230 lines, confidence 75%)

**Theme:** Every claim gets a structured confidence level with evidence type, output as inline labels and machine-readable JSON.

| # | Item | Module | What Changes | Est. Size |
|---|------|--------|-------------|-----------|
| H2-7 | Claim confidence data model | New `confidence.py` | `ClaimConfidence` (claim, tier, confidence 1-5, evidence_type, counter_evidence, source_ids), `ReportConfidenceProfile` | ~60 lines |
| H2-8 | Confidence extraction prompt | `synthesize.py` | New `extract_confidence_profile()` — separate pass after synthesis | ~70 lines |
| H2-9 | Inline confidence markers | `synthesize.py` | `[Low Confidence]` for <= 2, `[Disputed]` from C32, no marker for >= 4 | ~25 lines |
| H2-10 | Confidence profile persistence | `report_store.py` | `.confidence.json` sidecar file alongside report, uses `atomic_write()` | ~30 lines |
| H2-11 | Confidence-aware critique | `critique.py` | New `CLAIM_CONFIDENCE` dimension | ~25 lines |
| H2-12 | Per-context confidence thresholds | `context_result.py`, `context.py` | `confidence_flag_threshold: int = 2` on `ContextProfile` | ~20 lines |

**Dependencies:** C29 evidence-tier labeling (tier vocabulary), C32 counter-search (counter_evidence flag).

**Design notes:**
- Confidence 75%. Uncertain part: extraction prompt asking Claude to score its own claims.
- Separate pass (not inline during synthesis) to avoid prompt complexity degradation.
- JSON sidecar for machine-readable data, inline markers for human-readable report.
- New critique dimension changes mean score calculation for future critiques only.

**Acceptance criteria (EARS):**
- WHEN standard/deep mode completes THE SYSTEM SHALL produce `ReportConfidenceProfile` for every major claim
- WHEN claim has confidence <= 2 THE SYSTEM SHALL include `[Low Confidence]` inline marker
- WHEN auto-save is enabled THE SYSTEM SHALL write `.confidence.json` sidecar
- WHEN context has `confidence_flag_threshold: 3` THE SYSTEM SHALL flag claims <= 3
- WHEN mode is quick THE SYSTEM SHALL skip confidence extraction
- WHEN mean confidence < 2.5 THE SYSTEM SHALL log warning about low epistemic confidence

---

## Cycle 34: Research Memory That Compounds (6 sessions, ~320 lines, confidence 60%)

**Theme:** Persistent knowledge store queried at every run start, so the agent gets smarter over time.

*Note: Originally C35 in the brainstorm; moved up because it has higher workflow impact and stores structured data from C33.*

| # | Item | Module | What Changes | Est. Size |
|---|------|--------|-------------|-----------|
| H2-19 | Knowledge store data model | New `knowledge.py` | `KnowledgeEntry` (query, timestamp, claims from C33, counter_findings from C32, critique, gap_ids, mode, source_count), `KnowledgeStore` | ~50 lines |
| H2-20 | JSON persistence | `knowledge.py` | `save_entry()`, `load_store()` — flat JSON files, `atomic_write()` | ~60 lines |
| H2-21 | Knowledge query at run start | `knowledge.py`, `agent.py` | `query_knowledge()` — term overlap matching, top-3 relevant prior entries | ~50 lines |
| H2-22 | Injection into decomposition | `decompose.py` | `prior_knowledge` parameter, `<prior_knowledge>` XML block | ~30 lines |
| H2-23 | Injection into synthesis | `synthesize.py` | `<prior_knowledge>` XML block — build on prior findings, note confirmations/contradictions | ~40 lines |
| H2-24 | Accumulation after each run | `agent.py` | Build `KnowledgeEntry` from run results, save via `save_entry()` | ~30 lines |
| H2-25 | Per-context knowledge isolation | `knowledge.py`, `context_result.py` | `knowledge_dir: str` on `ContextProfile`, scoped storage | ~25 lines |
| H2-26 | Knowledge staleness and pruning | `knowledge.py` | 90-day TTL exclusion, explicit `prune_knowledge()`, warning at 200 entries | ~35 lines |

**Dependencies:** C33 confidence scoring (structured claims to store), C32 counter-search (disputed findings to store).

**Design notes:**
- Confidence 60%. Most ambitious cycle in H2.
- Flat JSON files (not SQLite) — zero database dependencies, matches existing patterns. Revisit at ~500 entries.
- Term-overlap matching may produce false positives — plan phase must evaluate whether LLM relevance check is needed.
- Does NOT replace gap schema (forward-looking) — knowledge store is backward-looking (what was found).
- Per-context isolation is critical (PFE knowledge must not leak into AGM queries).

**Acceptance criteria (EARS):**
- WHEN standard/deep completes with auto_save THE SYSTEM SHALL write `KnowledgeEntry` JSON
- WHEN new run starts on topic with prior entries THE SYSTEM SHALL inject up to 3 relevant entries into decomposition and synthesis
- WHEN prior knowledge contains `[Disputed]` claim THE SYSTEM SHALL include dispute status so new run can re-investigate
- WHEN context has `knowledge_dir: "memory/pfe"` THE SYSTEM SHALL scope to that directory
- WHEN entry older than 90 days THE SYSTEM SHALL exclude from query results
- WHEN store exceeds 200 entries THE SYSTEM SHALL log pruning recommendation
- WHEN mode is quick with auto_save=False THE SYSTEM SHALL skip persistence

---

## Cycle 35: Adaptive Mid-Flight Re-Planning (6 sessions, ~340 lines, confidence 65%)

**Theme:** Agent evaluates evidence quality after each search pass and adjusts strategy.

*Note: Originally C34 in the brainstorm; moved to last position — highest risk, most internal, benefits from all prior infrastructure.*

| # | Item | Module | What Changes | Est. Size |
|---|------|--------|-------------|-----------|
| H2-13 | Research plan data model | New `planner.py` | `ResearchPlan` (query, sub_queries, strategy, priority_areas, max_passes), `PlanRevision` (reason, action, new/dropped queries) | ~50 lines |
| H2-14 | Evidence quality assessment | `planner.py` | `assess_evidence_quality()` — score distribution + confidence spread + coverage gaps. Local computation, no LLM call. | ~60 lines |
| H2-15 | Plan revision logic | `planner.py` | `revise_plan()` — explicit if/elif rules, deterministic. LLM only for generating replacement queries. | ~80 lines |
| H2-16 | Adaptive loop in agent.py | `agent.py` | Replace fixed two-pass in `_research_deep()` with max-3-iteration loop. Standard mode: decide whether pass 2 is worth running. | ~100 lines |
| H2-17 | Logging and observability | `agent.py`, `planner.py` | `_adaptation_log: list[PlanRevision]`, INFO-level logging of decisions | ~30 lines |
| H2-18 | Mode parameters | `modes.py` | `adaptive_planning: bool`, `max_adaptive_passes: int`, `min_score_for_continue: float` | ~20 lines |

**Dependencies:** C33 confidence scoring (confidence_spread for assessment), C34 research memory (known facts inform planning), C29 score-aware refinement (generalized from binary to continuous).

**Design notes:**
- Confidence 65%. Riskiest cycle in H2.
- Explicit rules (not LLM-driven planning) for determinism and testability.
- Standard mode: conservative win (skip unnecessary pass 2). Deep mode: full adaptive loop.
- Refactoring risk: `_research_deep()` is ~85 lines. Mitigation: extract `_run_search_pass()` helper first (refactoring commit), then build loop (feature commit).
- Deep mode cost could double. Max 3 passes + total source budget cap prevents runaway costs.

**Acceptance criteria (EARS):**
- WHEN deep mode pass 1 mean score < 2.5 AND thin footprint THE SYSTEM SHALL stop early
- WHEN deep mode has bimodal scores THE SYSTEM SHALL drop low-scoring queries and add alternatives
- WHEN standard mode pass 1 has 4+ sources >= 4 THE SYSTEM SHALL skip pass 2
- WHEN adaptive loop reaches max passes THE SYSTEM SHALL proceed to synthesis
- WHEN plan revision occurs THE SYSTEM SHALL log at INFO level
- WHEN mode is quick THE SYSTEM SHALL skip all adaptive planning

---

## H2 Summary

| Cycle | Sessions | Lines | New Modules | Confidence |
|-------|----------|-------|-------------|------------|
| 32: Counter-Search | 5 | ~245 | — | 80% |
| 33: Confidence Scoring | 6 | ~230 | `confidence.py` | 75% |
| 34: Research Memory | 6 | ~320 | `knowledge.py` | 60% |
| 35: Adaptive Planning | 6 | ~340 | `planner.py` | 65% |
| **Total** | **23** | **~1135** | **3** | — |

Cross-cycle dependency chain:
```
C29 evidence-tier labels ──→ C32 claim extraction
C29 skeptic enforcement ───→ C32 prioritization by severity
C32 CounterSearchResult ───→ C33 ClaimConfidence.counter_evidence
C33 ClaimConfidence ────────→ C34 KnowledgeEntry.claims
C32 CounterSearchResult ───→ C34 KnowledgeEntry.counter_findings
C33 ReportConfidenceProfile → C35 EvidenceAssessment.confidence_spread
C34 KnowledgeEntry ─────────→ C35 planner has prior knowledge for decisions
```
