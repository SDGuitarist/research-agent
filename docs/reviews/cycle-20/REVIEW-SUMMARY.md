# Code Review: Cycle 20 — Query Iteration Integration

**Review Date:** 2026-03-02
**Branch:** `main`
**Commits:** `a603afc` (Session 1), `9db72c0` (Session 2)
**Changes:** +1,582 lines across 14 files
**Tests:** 869 pass (all green)

---

## Overall Assessment

The Cycle 20 query iteration feature is **well-implemented and architecturally sound**. It follows the codebase's established patterns (frozen dataclasses, sync+asyncio.to_thread, three-layer prompt injection defense, specific exception handling) with high consistency. The additive pattern is strictly maintained — the main report is never mutated. Error isolation is appropriate at two layers matching the skeptic pattern.

No P1 blockers prevent merge. The two P1 findings are a docstring gap and a dead parameter — quick fixes.

## Findings Summary

- **Total Findings:** 14
- **P1 (Critical):** 2 — documentation gap + dead parameter
- **P2 (Important):** 7 — security defense-in-depth, performance, parity, test coverage
- **P3 (Nice-to-Have):** 5 — style, naming, consistency

### Recommended Fix Order

| # | Issue | Priority | Why this order | Unblocks |
|---|-------|----------|---------------|----------|
| 1 | 100 - `skip_iteration` docstring gap | P1 | Quick fix, public API docs | — |
| 2 | 101 - unused `surviving` parameter | P1 | Dead code removal, 2 lines | — |
| 3 | 102 - unsanitized headings in prompts | P2 | Defense-in-depth gap, affects 2 files | 112 |
| 4 | 103 - sequential mini-report synthesis | P2 | Largest perf win (10-25s savings) | — |
| 5 | 104 - no overall iteration timeout | P2 | Safety net against 8-min worst case | — |
| 6 | 105 - CLI missing `--no-iteration` flag | P2 | Inverted parity gap | — |
| 7 | 106 - MCP tests for iteration params | P2 | Boundary test coverage | — |
| 8 | 107 - "skipped" status overloaded | P2 | API design clarity | — |
| 9 | 108 - truncate draft for refinement | P2 | Token cost + latency savings | — |
| 10 | 109 - hoist SynthesisError import | P3 | Style consistency | — |
| 11 | 110 - named constants for thresholds | P3 | Pattern consistency | — |
| 12 | 111 - skip_iteration naming inconsistency | P3 | Convention consistency | — |
| 13 | 112 - section title sanitization | P3 | Defense-in-depth consistency | — |
| 14 | 113 - cap iteration_max_tokens | P3 | Prevents bloated deep-mode sections | — |

## Review Agents Used

1. **kieran-python-reviewer** — Pythonic patterns, type safety, async/sync boundaries
2. **security-sentinel** — Prompt injection defense, SSRF, data leakage
3. **performance-oracle** — Parallelism strategy, API efficiency, timeouts
4. **architecture-strategist** — Module dependencies, integration points, additive pattern
5. **code-simplicity-reviewer** — YAGNI violations, dead code, over-engineering
6. **agent-native-reviewer** — MCP/CLI parity
7. **learnings-researcher** — Past solutions from docs/solutions/
8. **pattern-recognition-specialist** — Naming, conventions, anti-patterns

## Key Positive Notes (from agents)

- **Architecture is sound.** iterate.py maintains proper dependency direction (never imports from agent.py). Integration point after synthesis, before critique is correct.
- **Three-layer prompt injection defense** consistently applied across all new LLM call sites (sanitize + XML boundaries + system prompt warnings).
- **Error handling is precise.** IterationError wraps only API failures. Validation rejections return empty results silently. Agent catches IterationError gracefully.
- **Test coverage is thorough.** 67 new tests covering parsing edge cases, API error wrapping, sanitization verification, domain neutrality, and mode-level validation.
- **Non-streaming mini-reports** correctly uses `client.messages.create()` for intermediate computation.
- **No YAGNI violations found.** The feature is well-scoped with no premature abstractions.
- **Past solutions applied.** 8 relevant institutional learnings were identified and all major patterns were properly followed.

## Security Verification

All three plan-flagged security concerns were properly addressed:
1. **CRITICAL (draft sanitization):** Both `generate_refined_queries` and `generate_followup_questions` sanitize inputs with `sanitize_content()`, XML boundaries, and system prompt warnings.
2. **HIGH (mini-report defense):** `synthesize_mini_report()` reuses `_build_sources_context()` and copies the system prompt from `synthesize_report()`.
3. **MEDIUM (type-safe URL extraction):** `_urls_from_evaluation()` handles both SourceScore and dict types with explicit isinstance checks.

One defense-in-depth gap found: headings extracted from the report are injected into prompts without sanitization (Finding 102).

## Three Questions

1. **Hardest judgment call in this review?** Whether to flag the sequential mini-report synthesis (103) as P1 or P2. It adds 10-25s to every standard/deep query, which impacts user experience significantly. However, it's a performance optimization rather than a correctness bug, and the feature works correctly as-is. Settled on P2 because it doesn't block correctness.

2. **What did you consider flagging but chose not to, and why?** The "all summaries shared across all mini-reports" design (all iteration summaries go to every mini-report instead of partitioning by source query). Performance-oracle flagged this as an optimization opportunity, but the current approach works correctly (the LLM filters by relevance), and partitioning would require significant changes to `_search_sub_queries` return types. Deferred to a future cycle.

3. **What might this review have missed?** Real-world quality of the generated queries and mini-reports. All review agents analyzed code structure, security, and performance — but none can evaluate whether the gap-first refinement prompt actually produces useful queries different from decompose, or whether mini-reports with the heading exclusion list actually avoid repetition. The plan called for testing with 3 real queries; this review cannot verify that testing happened or what the results showed.
