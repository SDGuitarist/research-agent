# HANDOFF — Research Agent

**Date:** 2026-04-21
**Branch:** `main`
**Phase:** Brainstorm COMPLETE. Ready for C29 Plan.

## Current State

"10 Steps Ahead" strategic brainstorm complete — 3 horizons (H1: C29-31 foundation, H2: C32-35 structural leap, H3: C36-39 experience layer), 5 appendices, Codex review findings addressed, self-review passed. Brainstorm declared ready for Plan phase.

**Key commits this session:**
- `36fc689` — initial brainstorm
- `2a37659` — 5-agent deep research (cycle specs, context evolution, swarm, competitive landscape, prioritization)
- `8acc7f4` — Codex brainstorm review handoff
- `0252faa` — Codex review fixes (7 findings + 3 self-review fixes)

**Tests:** 1040 passing (no code changes this session — docs only)

## Key Decisions Made

1. **Positioning:** Generalized engine, business-specific configuration via context packages (agreed with user)
2. **H2 dependency chain:** C29→C32→C33→C34→C35 is sequential, not parallel
3. **H2 ordering:** C32 counter-search → C33 confidence → C34 memory → C35 adaptive planning
4. **ContextProfile:** 4→10 fields across H1/H2/H3 with path governance (one-hop, shared validation, read-only/read-write split)
5. **Dropped:** `preferred_sources` (YAGNI per C24), `source_config` moved to H3
6. **Swarm MVS:** 4 roles, unified skeptic pass preserved (no distribution in v1)
7. **Moat thesis:** Softened from "moat" to "positioning advantage" — holds while commercial incentives discourage self-doubt

## Top Risks (carried forward from brainstorm Feed-Forward)

1. **Search coverage dependency** — epistemic rigor sits on Tavily + DDG. C33 plan must decide: include "coverage confidence" or accept as structural risk.
2. **Adaptive planning (C35, 65%)** — overlaps iterate.py/coverage.py, riskiest refactor
3. **Confidence extraction prompt (C33)** — metacognitive, needs prototyping with 5 real reports

## Key Artifacts

| Artifact | Location |
|----------|----------|
| Brainstorm (main) | `docs/brainstorms/2026-04-21-ten-steps-ahead-brainstorm.md` |
| Appendix A: Competitive landscape | `docs/brainstorms/appendices/appendix-a-competitive-landscape.md` |
| Appendix B: H2 cycle specs | `docs/brainstorms/appendices/appendix-b-h2-cycle-specs.md` |
| Appendix C: ContextProfile evolution | `docs/brainstorms/appendices/appendix-c-context-profile-evolution.md` |
| Appendix D: Swarm architecture | `docs/brainstorms/appendices/appendix-d-swarm-architecture.md` |
| Appendix E: H2 prioritization | `docs/brainstorms/appendices/appendix-e-h2-prioritization.md` |
| Codex review handoff | `docs/brainstorms/2026-04-21-codex-brainstorm-review-handoff.md` |
| Entropy roadmap (C29-31 spec) | `docs/research/2026-03-09-entropy-fixes-roadmap.md` |

## Deferred Items

- **ANTHROPIC_ERRORS consumption at 10+ call sites** — mechanical replacement for micro-cycle
- **MCP `--cost` + `--critique-history` tools** (#123) — Cycle 31
- **A/B live validation** — run `scripts/validate_cutoff_ab.py` when API keys renewed

## Three Questions

1. **Hardest decision in this session?** H2 dependency chain. Codex caught that the brainstorm claimed C32-35 were "mostly independent" when they actually form a sequential chain. The correction was right — each cycle's data model feeds the next.
2. **What did you reject, and why?** `preferred_sources` on ContextProfile. Cycle 24 proved +0.5 on int scores with int cutoff is a no-op. Same issue applies. Don't add fields with zero behavioral effect.
3. **Least confident about going into plan?** Search coverage dependency. The brainstorm claims epistemic rigor as the differentiator, but every verification layer operates on whatever Tavily/DDG return. The C29 plan must decide whether to include "coverage confidence" in C33's scoring model or flag it as an accepted risk.

## Next Phase

**Plan** — Write C29 implementation plan (skeptic enforcement + score-aware refinement + evidence-tier labeling).

### Prompt for Next Session

```
Read HANDOFF.md and docs/research/2026-03-09-entropy-fixes-roadmap.md (C29 section).
Read docs/brainstorms/2026-04-21-ten-steps-ahead-brainstorm.md (Part 5 H1 modifications).
Write docs/plans/2026-04-21-cycle-29-skeptic-enforcement-plan.md.
Include EARS acceptance tests, Codex handoff prompt, Feed-Forward + Three Questions.
Address prior risk: decide whether C33 includes "coverage confidence" or accept as structural risk.
Do only the plan — commit and stop. Do NOT begin implementation.
Start with /compound-start to load lessons and kick off.
```
