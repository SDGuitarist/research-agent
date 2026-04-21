# Appendix D: Multi-Agent Research Swarm Architecture (C39)

**Source:** swarm-design agent, 2026-04-21

## Role Specifications (5 Core + 2 Optional)

| Role | What It Does | Consumes | Produces |
|------|-------------|----------|----------|
| **Coordinator** | Decomposes query, assigns facets, monitors progress, resolves convergence | Original query, ContextProfile, all agent outputs | Facet assignments, convergence decisions |
| **Domain Expert** (×N) | Deep research on assigned facet — runs full sub-pipeline (search→fetch→extract→summarize) | Assigned facet query, ContextProfile | Facet report, source list, evidence graph fragment |
| **Contrarian** | Searches for disconfirming evidence against each major claim | Domain Expert facet reports | Counter-evidence report, conflict annotations |
| **Verifier** | Scores every claim, cross-references sources, detects contradictions across facets | All facet reports + counter-evidence | Per-claim confidence scores, contradiction list |
| **Editor** | Synthesizes final report from verified evidence, applies tone and template | Verified reports, confidence scores, ContextProfile | Final markdown report, citations |
| *Temporal Analyst* (optional) | Evaluates time-sensitivity, flags stale data | Facet reports, gap schema history | Temporal annotations, staleness warnings |
| *Context Specialist* (optional) | Domain-specific search queries, industry vocabulary, source prioritization | ContextProfile specialist config | Search augmentation, terminology mapping |

## Communication: Phased Blackboard

In-memory shared dict (not filesystem). Reads only at phase boundaries.

```
Phase 1 (Plan):      Coordinator writes facet assignments
Phase 2 (Research):  Domain Experts write facet reports (parallel)
Phase 3 (Challenge): Contrarian writes counter-evidence
Phase 4 (Verify):    Verifier writes claim scores + gate decision
Phase 5 (Synthesize):Editor writes final report
```

**Why blackboard:** Agents don't need real-time conversation — they read completed outputs between phases. Same pattern as `skeptic.py`'s concurrent async agents.

**Why in-memory:** Agents are async coroutines in a single Python process (same as `run_deep_skeptic_pass`). Shared dict is simpler than file-based exchange.

## Conflict Resolution (Rule-Based, Not LLM)

- Contradiction between facets → preserve both, annotate confidence
- Unsupported claim found → downgrade evidence tier
- All claims on a facet unsupported → "Low Confidence" header
- Verifier gate = insufficient → ONE retry cycle, then insufficient_data response

No dedicated arbiter LLM. Verifier scores confidence. Editor handles presentation. Rules are deterministic.

## Pipeline Mapping

```
CURRENT                     SWARM                    WHO
decompose_query     →       Phase 1: Plan            Coordinator
search/fetch/       →       Phase 2: Research        Domain Experts (parallel)
extract/summarize
(nothing)           →       Phase 3: Challenge       Contrarian (NEW)
evaluate_sources    →       Phase 4: Verify          Verifier (extends relevance)
skeptic             →       DISTRIBUTED              Evidence→Verifier, Timing→Temporal, Frame→Contrarian
synthesize          →       Phase 5: Synthesize      Editor
```

**Key insight:** The swarm parallelizes the middle of the pipeline. It does not replace the pipeline. Existing modules (`search.py`, `fetch.py`, `extract.py`, `summarize.py`) become the sub-pipeline each Domain Expert runs.

## Shared Spec (~130 Lines)

Three sections:
1. **Data contracts** (~60 lines): `FacetAssignment`, `FacetReport`, `EvidenceNode`, `CounterClaim`, `ScoredClaim`
2. **Phase contracts** (~40 lines): What each phase reads/writes, no intra-phase reads
3. **Behavioral contracts** (~30 lines): Domain experts don't coordinate, contrarian must counter-search, verifier scores ALL claims, editor never drops contradictions

## Minimum Viable Swarm (4 Roles)

**Coordinator + 2 Domain Experts + Editor.** Proves parallel facet research before adding adversarial roles.

```
Coordinator → Domain Expert 1 || Domain Expert 2 → [unified skeptic pass] → Editor
```

**Skeptic in MVS: unified post-synthesis pass preserved.** The current `skeptic.py` three-lens pass (evidence, timing, strategic frame) runs as a single coordinated step after draft synthesis. The MVS keeps this unchanged rather than distributing lenses across swarm roles. Distributing the skeptic (evidence→Verifier, timing→Temporal, frame→Contrarian) is a later evolution (C39b+) that requires validating whether separated lenses maintain the same adversarial quality as the combined pass. The current `run_deep_skeptic_pass()` orchestration in `skeptic.py` passes prior findings to the frame lens (evidence and timing run independently, but the frame lens receives both as context). This cross-lens context would be lost if roles run independently in the swarm.

Quality gain: broader coverage (2 independent search strategies). Wall-clock savings: Phase 2 runs 2 facets in parallel.

Full 5-agent swarm (adding Contrarian + Verifier, potentially distributing skeptic) is C39b.

## 7+ Agent Boundary

| Agents | Depth | Risk |
|--------|-------|------|
| 5 (core) | 5 | Manageable DAG |
| 7 (+ Temporal + Context) | 6 (with parallel mitigation) | Untested — validate in isolation first |

Temporal Analyst runs in parallel with Contrarian (both read facet reports independently), keeping depth at 6 instead of 7. Never exceed 7 without isolated experiment.
