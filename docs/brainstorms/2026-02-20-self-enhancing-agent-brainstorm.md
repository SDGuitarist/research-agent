# Self-Enhancing Research Agent — Brainstorm

**Date:** 2026-02-20
**Cycle:** TBD (future)
**Status:** Brainstorm complete — ready for planning

---

## What We're Building

A feedback loop where the research agent critiques its own reports after writing them, records structured learnings, and uses those learnings to improve future runs — without modifying its own code.

This automates the "compound" phase of the compound engineering workflow. Instead of manually capturing lessons in `docs/solutions/`, the agent captures its own.

---

## Why This Matters

Right now the agent treats every run as independent. It doesn't learn from:
- Sources that turned out to be weak (press releases, outdated data)
- Geographic or topical blind spots in decomposition
- Queries where the skeptic found major issues
- Patterns in what makes a good vs. bad report

A human using the agent would naturally adjust their approach over time. This gives the agent the same ability.

---

## What We Already Have

| Component | Self-enhancement role |
|-----------|----------------------|
| `skeptic.py` | Already critiques reports for evidence, timing, framing |
| `relevance.py` | Already scores sources 1-5, gates output quality |
| `research_context.md` | External config that shapes prompts without code changes |
| `context.py` | Loads business context into prompts at runtime |
| `agent.py` | Exposes `_last_source_count`, `_last_gate_decision`, skeptic findings after each run |

The pieces exist. The gap is connecting them into a persistent feedback loop.

---

## Scope: Tier 1 + Tier 2

### Tier 1: Self-Critique Log

After every report, the agent runs an evaluation pass and writes structured YAML:

```yaml
# reports/meta/critique-ai-music-licensing_2026-02-20T14-30.yaml
query: "AI music licensing trends"
mode: standard
timestamp: "2026-02-20T14:30:00"
scores:
  source_diversity: 3       # 1-5, variety of source types/domains
  claim_support: 4           # 1-5, how well claims are backed by evidence
  coverage: 2                # 1-5, how thoroughly the query was answered
  geographic_balance: 2      # 1-5, diversity of geographic perspectives
weaknesses:
  - "Only found US-centric sources, missed EU regulations"
  - "3 of 10 sources were press releases, not primary"
suggestions:
  - "Add geographic diversity to search decomposition"
  - "Penalize PR/marketing sources in relevance scoring"
skeptic_flags:
  - type: evidence
    detail: "Revenue claim cited blog post, not industry report"
gate_decision: full_report
source_count: 8
dropped_count: 2
```

**What this gives us:** A knowledge base of agent performance over time. No behavior changes yet — just structured data.

**New code:** One module (`critique.py`), called at the end of `agent.py` after report generation. Follows the additive pattern — no changes to existing modules.

### Tier 2: Adaptive Prompts

The agent reads the last 10 critiques and injects lessons into its prompts at runtime.

**How it works:**
1. `context.py` gets a new `load_critique_history()` function that reads recent critique YAMLs
2. `decompose.py` receives critique-informed context in its prompt — e.g., "In past runs, geographic diversity scored low. Generate at least one sub-query targeting non-US sources."
3. `relevance.py` receives scoring adjustments — e.g., "Press releases and marketing content scored poorly in past evaluations. Apply stricter scoring."

**Why this is safe:**
- Prompts are ephemeral — bad adaptations don't persist in code
- The underlying logic never changes
- Every adaptation is traceable back to a specific critique
- You can inspect what adaptations were applied (see Transparency below)

**New code:** Extend `context.py` with `load_critique_history()`. Modify prompt construction in `decompose.py` and `relevance.py` to accept optional critique context.

---

## Key Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Scope | Tier 1 + Tier 2 | Closes the feedback loop without self-modification risk |
| 2 | Critique trigger | Always automatic | Simpler, builds data faster, no flag to forget |
| 3 | Storage location | `reports/meta/` | Critiques live alongside the reports they evaluate |
| 4 | Storage format | YAML | Human-readable, easy to load, matches existing patterns |
| 5 | History depth | Last 10 critiques | Good balance of signal vs. noise for adaptive prompts |
| 6 | Transparency | "Lessons Applied" section in report | Makes the feedback loop visible to the user |
| 7 | Self-modification | None — prompt-only adaptations | Safe, reversible, inspectable |

---

## Architecture

```
Run N:
  agent.py (after synthesis)
    → critique.py — evaluates report quality, writes YAML to reports/meta/

Run N+1:
  context.py — load_critique_history() reads last 10 critiques
    → decompose.py — receives critique-informed suggestions in prompt
    → relevance.py — receives scoring adjustments from critique patterns
    → synthesize.py — appends "Lessons Applied" section to report
```

Data flow:
```
report → critique.py → reports/meta/critique-{query}_{timestamp}.yaml
                              ↓
              context.py reads critiques on next run
                              ↓
              decompose.py + relevance.py receive adaptive context
                              ↓
              report includes "Lessons Applied" section
```

---

## New Modules & Changes

| Module | Change | Estimated size |
|--------|--------|---------------|
| `critique.py` (new) | Post-report evaluation, YAML output | ~100-150 lines |
| `context.py` (extend) | `load_critique_history()` function | ~50-80 lines |
| `decompose.py` (modify) | Accept + use critique context in prompt | ~20-30 lines |
| `relevance.py` (modify) | Accept + use scoring adjustments from critiques | ~20-30 lines |
| `synthesize.py` (modify) | Append "Lessons Applied" section | ~15-20 lines |
| `agent.py` (modify) | Call critique after synthesis, pass critique context through pipeline | ~20-30 lines |

**Total new code:** ~230-340 lines across 3-4 sessions.

---

## What Gets Critiqued

All evaluation dimensions use data already produced by the pipeline:

| Dimension | Source |
|-----------|--------|
| Source diversity | Count unique domains/source types from surviving sources |
| Claim support | Skeptic evidence findings (critical count, concern count) |
| Coverage | Compare sub-queries generated vs. sub-queries with good sources |
| Geographic balance | Analyze source URLs/content for geographic spread |
| Gate decision | Already computed by `relevance.py` |
| Dropped sources | Already tracked by `RelevanceEvaluation` |

No new evaluation logic needed — `critique.py` aggregates and scores what already exists.

---

## Research Findings

### Best Practices (from industry research)

**OpenAI Self-Evolving Agents Cookbook** describes exactly this pattern: a repeatable retraining loop that captures issues, learns from feedback, and promotes improvements. Three optimization strategies ranging from manual iteration to fully automated loops. Key insight: combine LLM-as-judge evals with human review checkpoints.

**Anthropic Context Engineering** paper confirms: "the best form of feedback is providing clearly defined rules for an output, then explaining which rules failed and why." This validates structured critique with specific dimensions over vague "improve quality" instructions.

**SAFLA framework** (Python, pip-installable) is a reference implementation of self-aware feedback loops with episodic memory — far more complex than needed, but validates the architectural approach.

### DSPy Patterns Worth Borrowing (no DSPy dependency)

1. **Dual-mode metrics** — Use both a gate score (pass/fail: is this report deliverable?) AND dimensional scores (floats: how good is each aspect?). The gate prevents bad reports from polluting critique history. Applied: `CritiqueResult.overall_pass` (gate) + per-dimension scores (floats).

2. **Grounded instruction proposals** — Don't inject vague "improve source diversity." Instead, include the actual weakness text from the critique. Bad: `"source diversity was low."` Good: `"Report cites 4 sources but 3 are from tripadvisor.com. No industry reports cited."`

3. **Baseline anchor (candidate #0)** — DSPy always keeps the original unoptimized prompt as a candidate. If no optimization beats it, the original survives. Applied: compare critique-injected runs vs. pre-injection baseline. If injection makes things worse, disable it automatically.

4. **Minimum data thresholds** — Don't inject critique-derived instructions until 3+ critiques exist. Don't promote a pattern to "persistent improvement" until consistent across 5+ runs.

5. **Strict bootstrapping** — If building a "good reports" bank later, only store reports that passed the overall gate. Don't cherry-pick sections from otherwise-failed reports.

### Edge Cases & Risks (ranked by priority)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| **Prompt injection via critique** | Medium | Critical | Never store raw web content in YAML. Apply `sanitize_content()` to all fields. Summarize patterns, don't paste raw text verbatim. Validate against strict schema on load. |
| **Feedback loop mode collapse** | High | High | Sliding window of 10 critiques. Track score standard deviation — if it drops below 0.3, the agent is converging on one style. Alert. |
| **Score calibration drift** | High | Medium | Z-score normalization within rolling window. Store model version with every score. Use temperature 0 for critique calls. |
| **Cold start instability** | Medium | Medium | Don't activate adaptive prompts until 3+ critiques exist. Omit the section entirely — never show empty headers. |
| **Stale/contradictory critiques** | High | Medium | Tag critiques with query domain + TTL (30 days). Only load domain-matching critiques. Detect contradictions before injection. |
| **MemoryGraft-style memory poisoning** | Low | Critical | Critique fields limited to structured scores (ints) + short sanitized text (max 200 chars). Never inject critique text verbatim into prompts. |
| **File corruption** | Low | High | Use existing `safe_io.py` for atomic writes. Validate schema on load, skip corrupt files silently. Retention policy: max 50 files. |
| **Performance overhead** | Low | Low | ~$0.03/run extra (~10-20%). Make critique async — generate after report is returned to user. Skip critique in `--quick` mode. |

### Research-Informed Design Refinements

Based on the research, these changes to the original brainstorm:

1. **Add `overall_pass` gate to critique** — A report must score mean >= 3.0 with no dimension below 2.0 to "pass." Only passing reports contribute to adaptive prompt history.
2. **Add `query_domain` field to critique YAML** — Prevents cross-domain contamination (financial critique patterns leaking into entertainment queries).
3. **Add `model_version` field** — Enables score comparability across model updates.
4. **Summarize patterns, never paste raw critique text** — "3 of 5 recent critiques flagged weak evidence" is safer than pasting the actual weakness text (prompt injection vector).
5. **Make critique async** — Run after report is saved and returned. User doesn't wait for it.
6. **Skip critique in `--quick` mode** — Quick mode prioritizes speed.

---

## Open Questions (Refined)

1. **Critique scoring: LLM vs. heuristic?** Research suggests LLM-as-judge with structured rubric. Cost: ~$0.02/call. Heuristic would be cheaper but can't assess analytical depth or actionability.
2. **Single file vs. many files?** Research suggests a single `reports/meta/critiques.yaml` with append-only semantics is simpler to manage, lock, and prune than one file per run. Trade-off: atomic append is more complex than atomic file write.
3. **Domain classification:** How to tag query domain automatically? Could use the decompose step's classification (SIMPLE/COMPLEX) or add a lightweight domain classifier.
4. **Baseline measurement:** Run 5 reports without critique injection first to establish baseline scores. Then compare.

---

## What We're NOT Building (Yet)

- **Tier 3 — Parameter tuning:** Auto-adjusting config values. Needs 20+ runs of critique data first.
- **Tier 4 — Recursive self-optimization:** Agent rewriting its own prompts/code. Too risky without benchmarks.
- **Benchmark suite:** Standardized queries to test against. Valuable but separate effort.
- **Dashboard:** Visual tracking of critique scores over time. Nice-to-have, not needed for the loop.

---

## Connection to Compound Engineering

This is the compound framework applied to the agent itself:

| Compound phase | Human version | Agent version |
|---------------|--------------|---------------|
| Brainstorm | Think about what went wrong | Critique pass analyzes report |
| Plan | Decide what to change | Suggestions written to YAML |
| Work | Implement the change | Prompt adaptations applied next run |
| Review | Check if it helped | Compare critique scores over time |
| Compound | Write it down | Critique YAML persists as knowledge |

---

## Three Questions

1. **Hardest decision in this session?**
   Single file vs. many files for critique storage. Many files (one per run) align with the existing `safe_io.py` atomic write pattern and avoid append-locking complexity — but a single file would be simpler to prune and query. Leaning toward many files because it matches how the rest of the codebase works (one report = one file), but this needs a final call in the plan.

2. **What did you reject, and why?**
   Rejected Tier 3 (parameter tuning) and Tier 4 (recursive self-optimization) for this cycle. Both require a meaningful body of critique data to work against, and the risk profile jumps sharply — parameter tuning can silently degrade quality, and self-modification is irreversible without version control on prompts. Tier 1 + Tier 2 close the feedback loop with zero self-modification risk.

3. **Least confident about going into the next phase?**
   Prompt injection through critique YAML. The brainstorm identified the risk and proposed mitigations (sanitize, summarize patterns instead of raw text, schema validation), but the plan needs to nail down exactly what gets sanitized and where — the boundary between "structured score" and "free-text suggestion" is where the attack surface lives.
