# Review Context — Research Agent

## Risk Chain

**Entropy audit risk:** "The code is the prompter — every entropy principle applies at the system level, but with no human review of intermediate prompts."

**Audit findings:** 10 findings across 5 entropy problem categories. Highest severity: no vague query detection (#1), skeptic findings not enforced (#7), quick mode single-source reports (#9).

**Roadmap:** 4 cycles (27-30) planned, dependency-ordered. Cycle 27 targets input validation + sanitization. See `docs/research/2026-03-09-entropy-fixes-roadmap.md`.

**Current cycle status:** Cycle 26 (MCP parity lint) in progress. Entropy fixes start at Cycle 27.

## Files to Scrutinize (Entropy Audit — Future Cycles)

| File | Finding | Risk area |
|------|---------|-----------|
| `research_agent/decompose.py` | #1 — No vague query validation | Noise enters pipeline unchecked |
| `research_agent/sanitize.py` | #8 — Non-idempotent sanitization | Data corruption across all stages |
| `research_agent/relevance.py` | #2, #3 — Permissive cutoff, no diversity | Noise/homogeneous sources pass through |
| `research_agent/cascade.py` | #6 — Snippet treated as full content | Thin sources weighted equally |
| `research_agent/modes.py` | #9 — Quick mode single-source reports | Hallucination vector |
| `research_agent/synthesize.py` | #7 — Skeptic not enforced | Critical findings ignored in output |
| `research_agent/search.py` | #10 — Refinement loop on noise | Feedback loop amplifies bad results |
| `research_agent/summarize.py` | #4 — Chunking loses context | Knowledge vacuum in synthesizer |
| `research_agent/token_budget.py` | #5 — Character-level truncation | False precision from mid-fact cuts |

## Key Research References

- `docs/research/2026-03-09-entropy-and-prompting-report.md` — Theory (entropy collapse, hallucination, S/N, web search, knowledge vacuums)
- `docs/research/2026-03-09-research-agent-entropy-audit.md` — 10 findings mapped to codebase
- `docs/research/2026-03-09-entropy-fixes-roadmap.md` — 4-cycle implementation plan

## Plan Reference

Cycle 26: `docs/plans/2026-03-08-cycle-26-mcp-parity-lint-plan.md`
Cycles 27-30: `docs/research/2026-03-09-entropy-fixes-roadmap.md`
