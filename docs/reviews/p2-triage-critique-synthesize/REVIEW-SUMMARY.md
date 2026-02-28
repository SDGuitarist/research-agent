---
title: "Review: P2 Triage — Critique & Synthesize Cleanup"
date: 2026-02-28
commits: ["3ef62ea", "c0e9805"]
plan: docs/plans/2026-02-28-refactor-p2-triage-critique-synthesize-plan.md
agents:
  - kieran-python-reviewer
  - code-simplicity-reviewer
  - pattern-recognition-specialist
  - architecture-strategist
  - agent-native-reviewer
  - learnings-researcher
---

# Review: P2 Triage — Critique & Synthesize Cleanup

## Overall Assessment

**Verdict: PASS — clean, well-scoped subtractive refactoring.**

This is a textbook YAGNI cleanup with good test coverage. The `query_domain` removal is thorough (13 sites), the factory classmethods match established codebase patterns, `dataclasses.asdict()` eliminates manual dict drift, and the `_build_default_final_sections` extraction is proportional. Net line count decreased. All 764 tests pass.

No P1 findings. Two P2 findings and two P3 findings, all with small fixes.

## Severity Snapshot

| Priority | Count |
|----------|-------|
| P1 (Critical) | 0 |
| P2 (Important) | 2 |
| P3 (Nice-to-have) | 2 |

## Recommended Fix Order

| # | Issue | Priority | Why this order | Unblocks |
|---|-------|----------|---------------|----------|
| 1 | 085 — Stale "Section 11" refs in synthesize.py | P2 | Misleads both LLM (prompt ambiguity) and developers (wrong docstring); highest blast radius | 086 |
| 2 | 087 — `from_parsed` type hint inaccuracy | P2 | One-line fix; independent of #1 | — |
| 3 | 086 — Stale test name `test_skips_section_11_when_no_findings` | P3 | Dependent on #085; rename in same pass | — |
| 4 | 088 — `_DEFAULT_FINAL_START = 5` coupling | P3 | Independent; low blast radius; acceptable as-is | — |

## Agent Reports

### kieran-python-reviewer
- **0 P1, 1 P2, 4 P3** — Flagged stale Section 11 refs (P2), stale test name (P3), asymmetric sanitization docs (P3), `_DEFAULT_FINAL_START` coupling (P3), `_parse_critique_response` return type (P3)
- Positive: keyword test construction, `asdict()` replacement, factory classmethods, extracted helper all praised

### code-simplicity-reviewer
- **0 P1, 0 P2, 3 P3** — All "keep as-is" observations. `_scores` property (could be explicit tuple), `from_parsed` validation (appropriate for constructor), `_DEFAULT_FINAL_START` coupling
- Verdict: "No changes needed. Code is simpler after these commits than before."

### pattern-recognition-specialist
- **0 P1, 2 P2, 3 P3** — Flagged `fallback()` naming inconsistency with ContextResult vocabulary (P2), `_build_default_final_sections` naming asymmetry (P2), type hint (P3), test verbosity (P3), coupling (P3)
- Note: Both naming P2s were deliberate plan decisions after deepening with 3 agents. `fallback` was chosen over `defaults` per brainstorm, `_build_default_*` was chosen over `_build_generic_*` per codebase precedent. **Discarded as accepted design decisions.**

### architecture-strategist
- **0 P1, 1 P2, 2 P3** — Flagged `from_parsed` type hint (P2), `_DEFAULT_FINAL_START` coupling (P3), `asdict()` future complex fields (P3 observation only)
- Confirmed: factory pattern matches ContextResult/ResearchMode. Backward YAML compatibility verified. Sanitization boundary preserved correctly.

### agent-native-reviewer
- **0 findings** — All 10 capabilities preserved. No regressions. Backward file globbing verified.

### learnings-researcher
- Surfaced 6 relevant past solutions
- **Key confirmation:** Asymmetric sanitization between `evaluate_report` (no sanitize) and `critique_report_file` (sanitizes) is **correct** per documented pattern in `docs/solutions/security/non-idempotent-sanitization-double-encode.md`
- The sanitize-at-boundary convention is: sanitize where untrusted data enters; `evaluate_report` data comes from Claude (trusted), `critique_report_file` data comes from disk (untrusted)
- No new sanitization boundaries were created by the helper extraction

## Discarded Findings

1. **`fallback()` naming** (pattern-recognition P2) — Deliberate plan decision after deepening with 3 agents. Brainstorm explicitly chose `fallback` over `defaults`. Matches codebase "fallback" vocabulary (cascade fallback, snippet fallback, search fallback).

2. **`_build_default_final_sections` naming** (pattern-recognition P2) — Plan explicitly chose this over `_build_generic_*` per `_default_critique` naming precedent and no `_generic_` prefix in codebase.

3. **Asymmetric sanitization** (kieran-python P3) — Confirmed correct per institutional pattern. `evaluate_report` trusts Claude output; `critique_report_file` sanitizes disk input. Documented in solution docs.

4. **`_scores` property style** (code-simplicity P3) — `getattr`+DIMENSIONS is DRY with `from_parsed`/`fallback`/`_parse_critique_response`. Consistent pattern, not a defect.

5. **Test construction verbosity** (pattern-recognition P3) — Keyword args are explicit and clear. 12 sites is manageable. Not worth a shared helper for a frozen dataclass.

## Three Questions

1. **Hardest judgment call in this review?** Whether the `fallback()` and `_build_default_final_sections` naming P2s from pattern-recognition-specialist were real findings or accepted design decisions. Both were explicitly decided in the plan after deepening with 3 review agents, with documented rationale. Discarded them as deliberate choices, not oversights.

2. **What did you consider flagging but chose not to, and why?** The `_parse_critique_response` return type (`-> dict` with no type params) — it's a private function exempt by convention, and adding `-> dict[str, int | str]` is related to but separate from the `from_parsed` type hint issue. Folding it into #087 would add scope to a one-line fix.

3. **What might this review have missed?** Whether the LLM actually produces better output with "Section 11" or "the **Adversarial Analysis** section" in the prompt. The stale section number may have been compensated for by the LLM seeing the actual numbered list earlier in the prompt. Fixing #085 is still correct (reduces ambiguity), but the behavioral impact on report quality is unknowable without A/B testing.
