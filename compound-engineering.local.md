# Review Context — Research Agent

## Risk Chain

**Audit trigger:** 6-agent comprehensive codebase audit after 28 development cycles identified 14 P2 findings.

**Plan mitigation:** 5-session dependency-ordered plan with explicit "What must NOT change" invariants (API call count, pipeline behavior, mode thresholds).

**Work risk (from Feed-Forward):** "compute_gate_decision rationale extraction — verbose vs terse distinction via context parameter."

**Review resolution:** 3 findings. (1) verbose/terse rationale — suffix approach was wrong, split into `verbose=True/False` with two private helpers. (2) SSRF pre-check needed regression tests. (3) GateDecision export needed explicit public API documentation. All fixed.

**Compound lesson:** When extracting duplicated logic where call sites produce structurally different output, use a mode parameter with separate format functions — not a modifier on the default format. Test exact output shapes, not just substring presence.

## Files to Scrutinize

| File | What changed | Risk area |
|------|-------------|-----------|
| `research_agent/errors.py` | `GateDecision` StrEnum, `ANTHROPIC_ERRORS` tuple | New public API export; ANTHROPIC_ERRORS not yet consumed at all 10+ sites |
| `research_agent/relevance.py` | `compute_gate_decision()` with verbose/terse, inlined instructions, BATCH_SIZE 5→10 | Two format helpers must stay in sync with decision branches; concurrency change |
| `research_agent/synthesize.py` | `_synthesis_errors(label)` context manager across 4 functions | Error message prefixes must match for log grep-ability |
| `research_agent/fetch.py` | `is_safe_url` (was `_is_safe_url`), httpx SSRF pre-check | Rename affects all test mock paths |
| `research_agent/cascade.py` | `extract_domains` parameter, deleted `EXTRACT_DOMAINS` constant | No-context fallback must skip layer 2 entirely |
| `research_agent/context_result.py` | `extract_domains` field on `ContextProfile` | New frozen dataclass field with default |
| `research_agent/search.py` | `get_tavily_client` (was `_get_tavily_client`), thread-safe cache | Cache reset needed in test fixtures |

## Deferred Items Tracking

| Item | Deferral Count | Rule |
|------|---------------|------|
| ANTHROPIC_ERRORS consumption at 10+ call sites | 1 | Mechanical replacement — do in next micro-cycle |
| MCP `--cost` + `--critique-history` tools (#123) | 2 | Promoted to Cycle 31 |
| A/B live validation (cutoff 3 vs 4) | 1 | Run `scripts/validate_cutoff_ab.py` when API key renewed |
| Session 5a smoke test (429 cascade check) | 1 | Run `--standard` query, check for sustained 429s |

## Plan Reference

`docs/plans/2026-04-07-cycle-29h-codebase-hygiene-plan.md`
Entropy roadmap (cycles 27-31): `docs/research/2026-03-09-entropy-fixes-roadmap.md`
