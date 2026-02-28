# Review Summary: Template-per-Context YAML Headers

**Target:** 3 commits on `main` (5752f82, eb3d838, e734b57)
**Date:** 2026-02-27
**Phase:** Review (compound engineering loop)

---

## Prior Phase Risk

> "Least confident about going into review? The `has_context` → `template` parameter change in `synthesize_draft()`. This is a public API change. All internal callers were updated, but if any external code calls `synthesize_draft(has_context=True)`, it will get a TypeError."

**Resolution:** Architecture Strategist confirmed this is low risk. `synthesize_draft`, `synthesize_final`, and `synthesize_report` are NOT in `__all__` in `__init__.py`. They are only imported in `agent.py` (production) and `test_synthesize.py` (tests). Both were updated. The public API surface (`run_research`, `run_research_async`, `ResearchAgent.research`) is unchanged. Pre-1.0 package, breaking internal changes are expected.

---

## Findings Summary

- **Total Findings:** 10
- **P1 (Critical):** 2 — logic bugs in YAML parsing
- **P2 (Important):** 6 — security boundary, simplification, API, code quality
- **P3 (Nice-to-Have):** 2 — consistency, defense-in-depth

### Severity Snapshot

| Priority | Count | Blocks Merge? |
|----------|-------|---------------|
| P1 | 2 | Yes |
| P2 | 6 | No |
| P3 | 2 | No |

---

## Recommended Fix Order

| # | Issue | Priority | Why this order | Unblocks |
|---|-------|----------|---------------|----------|
| 1 | 075 - `body if body else raw` leaks YAML | P1 | Logic bug — YAML syntax in prompts when file is all frontmatter | 077, 079 |
| 2 | 076 - YAML delimiter edge case | P1 | Independent, defensive hardening of parser | — |
| 3 | 077 - Sanitize template field values | P2 | Root cause — closes security gap for all template fields in prompts | — |
| 4 | 078 - Remove legacy PFE fallback branches | P2 | Completes decoupling goal, removes 18 lines + last PFE strings | — |
| 5 | 079 - Validate non-empty sections | P2 | Prevents subtle mixed template/generic behavior | — |
| 6 | 080 - Export ReportTemplate/ContextResult | P2 | Agent discoverability, one-time API fix | — |
| 7 | 081 - Replace mutable counter with enumerate | P2 | Prevents off-by-one on future changes | — |
| 8 | 082 - Bare `list` type hint | P2 | One-line clarity fix | — |
| 9 | 083 - f-string logging consistency | P3 | Style nit | — |
| 10 | 084 - YAML frontmatter size limit | P3 | Optional defense-in-depth | — |

---

## Review Agents Used

| Agent | Key Findings |
|-------|-------------|
| **security-sentinel** | Template fields unsanitized in prompts (P2), YAML safe_load sufficient, path traversal solid |
| **architecture-strategist** | Template-on-ContextResult acceptable, legacy fallback complexity, empty sections edge case |
| **kieran-python-reviewer** | YAML delimiter bug (P1), body fallback bug (P1), type hints, mutable counter |
| **performance-oracle** | No concerns — all operations sub-millisecond vs. multi-second API calls |
| **code-simplicity-reviewer** | Remove 18-line legacy branch, PFE-specific fallback strings remain |
| **agent-native-reviewer** | Types not exported, no programmatic template injection, silent validation |
| **learnings-researcher** | 6 relevant past solutions — bool-is-int YAML, sanitization boundaries, conditional templates |

---

## What Agents Agreed On

- **Architecture is sound.** The additive pattern (template layers on top without restructuring pipeline) is correct.
- **Frozen dataclass for ReportTemplate** is the right pattern, consistent with ResearchMode and CycleConfig.
- **YAML parsing before sanitization** is correctly ordered and well-reasoned.
- **Graceful degradation** (never crashes on malformed YAML) follows project convention.
- **Test coverage is thorough** — 748 tests passing, all new code paths covered.
- **Performance is a non-issue** — template operations are microseconds vs. multi-second API calls.

## What Agents Disagreed On

- **Template on ContextResult:** Architecture says it mixes concerns (content + config), but all agents agree it's pragmatically acceptable for a single-template system.
- **Legacy fallback branches:** Architecture says document as deprecation path; Simplicity says remove now. Simplicity is correct — the PFE-specific strings are the exact coupling this feature was designed to eliminate.

---

## Positive Findings

1. **Clean commit sequence:** Each commit has a single concern (data model → wiring → cleanup)
2. **No PFE-specific code in modes.py anymore** — synthesis_instructions are genuinely generic
3. **Path traversal defenses are solid** — two-layer defense, well-tested
4. **`yaml.safe_load()` is correct** — prevents code execution, sufficient for local files
5. **Backward compatibility preserved** — template=None falls back to existing behavior

---

## Learnings Researcher: Institutional Knowledge Applied

| Past Solution | Relevance | Status |
|--------------|-----------|--------|
| `python-bool-is-int-yaml-validation.md` | YAML validation boundary | ✅ Not applicable — no int fields in ReportTemplate |
| `conditional-prompt-templates-by-context.md` | Template branching pattern | ✅ Correctly applied |
| `non-idempotent-sanitization-double-encode.md` | Sanitize once at boundary | ⚠️ Template fields bypass this — see todo 077 |
| `pip-installable-package-and-public-api.md` | API export conventions | ⚠️ New types not exported — see todo 080 |
| `context-path-traversal-defense-and-sanitization.md` | Context security patterns | ✅ All patterns applied |
| `adversarial-verification-pipeline.md` | Draft→skeptic→final pipeline | ✅ Template correctly threads through |

---

## Three Questions

1. **Hardest judgment call in this review?** Whether the `elif context` legacy branch (finding 078) should be kept for backward compatibility or removed as dead PFE-specific code. Decided: remove it. The branch's hardcoded "Competitive Implications" and "Positioning Advice" sections are the exact coupling this feature eliminates. The generic `else` branch already handles context-without-template correctly.

2. **What did you consider flagging but chose not to, and why?** The agent-native reviewer flagged "no programmatic way to inject ReportTemplate without a file" (requires adding `context_result` parameter to `ResearchAgent.__init__`). This is a real gap but it's a feature request, not a bug in the current implementation. Logged as an observation, not a todo — the current file-based interface is sufficient for the single-user CLI use case.

3. **What might this review have missed?** The template feature has been validated against exactly one input shape (PFE context file). If a second context file is added with a different structure (e.g., no `final` sections, no `context_usage`, very long descriptions), edge cases may surface. The empty-sections validation (todo 079) partially addresses this, but a comprehensive "template schema documentation" effort would help catch the rest.

---

## Next Steps

1. **Fix P1 findings** (075, 076) — blocks merge
2. **Triage P2 findings** — recommend fixing 077-078 before compounding
3. **P3 findings** can be batched with other cleanup work
4. Run `python3 -m pytest tests/ -v` after all fixes to verify no regressions
