# Code Review Summary

**PR:** Self-Enhancing Agent (self-critique feedback loop)
**Branch:** self-enhancing-agent (bad292e..57bf44e, 4 commits, 12 files, +1091 -25)
**Date:** 2026-02-23
**Agents Used:** kieran-python-reviewer, pattern-recognition-specialist, code-simplicity-reviewer, architecture-strategist, security-sentinel, performance-oracle, data-integrity-guardian, git-history-analyzer, agent-native-reviewer

---

## P1 — Critical (Blocks Merge)

### 1. Bare `except Exception` Disguised as Specific Handling
- **Source Agents:** kieran-python (P1), pattern-recognition (P1), code-simplicity (P2), architecture (P2), security (P2), performance (P2), data-integrity (P2), git-history (P2) — **flagged by 8 of 9 agents**
- **File:** research_agent/agent.py:155
- **Issue:** `except (CritiqueError, Exception) as e:` catches everything. `CritiqueError` in the tuple is redundant. Violates project convention "Never bare `except Exception`." Git history shows this exact anti-pattern was previously fixed in commit `ac4e7ae` — re-introducing it is a regression.
- **Fix:** Narrow to specific exceptions: `except (CritiqueError, OSError, yaml.YAMLError) as e:` and add the specific Anthropic API error types. If a safety net is needed, add a separate `except Exception: logger.exception("Unexpected critique failure")`.

### 2. Critique Has No CLI Entry Point
- **Source Agent:** agent-native-reviewer (P1)
- **File:** research_agent/agent.py:126-157, cli.py (no --critique flag)
- **Issue:** Self-critique only runs as a hidden side effect of `--standard` or `--deep` runs. An agent orchestrating this tool cannot invoke critique independently, re-evaluate a previous report, or critique a report from a different source.
- **Fix:** Add `--critique <report-path>` CLI subcommand that outputs CritiqueResult.

### 3. Critique Results Invisible to CLI Consumers
- **Source Agent:** agent-native-reviewer (P1)
- **File:** research_agent/agent.py:151-153, cli.py (no critique output)
- **Issue:** After research completes, CLI prints the report but says nothing about critique scores. Results silently written to YAML. Classic "silent action" anti-pattern — agents and users get zero quality feedback.
- **Fix:** Print one-line summary to stdout after report: `Self-critique: mean=3.8, pass=True (reports/meta/critique-music_1234567890.yaml)`

### 4. Critique History Has No CLI Read Path
- **Source Agent:** agent-native-reviewer (P1)
- **File:** research_agent/context.py:228-285 (internal function only)
- **Issue:** `load_critique_history()` does exactly the aggregation agents need but has no CLI exposure. Agents cannot ask "what are my recurring weaknesses?" without parsing YAML files manually.
- **Fix:** Add `--critique-history` CLI flag to print summarized patterns.

---

## P2 — Important (Should Fix)

### 5. Hardcoded `Path("reports/meta")` in Two Independent Places
- **Source Agents:** kieran-python, pattern-recognition, architecture, data-integrity, agent-native, security, performance — **7 agents**
- **File:** research_agent/agent.py:149 and :193
- **Issue:** Write path and read path are independent string literals. CWD-dependent. If invoked from a different directory, critique history is silently empty forever. Inconsistent with how `schema_path` is handled via constructor.
- **Fix:** Extract to `META_DIR = Path("reports/meta")` constant or add `meta_dir` constructor parameter.

### 6. `CritiqueError` Defined but Never Raised (Dead Code)
- **Source Agents:** kieran-python (P2), pattern-recognition (P2), code-simplicity (P2), architecture (P3)
- **File:** research_agent/errors.py:48-50
- **Issue:** Exception class defined, imported, and caught — but nothing ever raises it. `evaluate_report` catches errors internally and returns defaults. Dead code creating false sense of structured error handling.
- **Fix:** Remove `CritiqueError` until actually needed, or have critique functions raise it.

### 7. Synchronous Blocking I/O in Async Context
- **Source Agents:** performance (P2), data-integrity (P2)
- **File:** research_agent/agent.py:193 (load_critique_history) and :126-156 (_run_critique)
- **Issue:** `load_critique_history` performs ~20 blocking syscalls (glob, stat, read_text, yaml.safe_load) on the event loop. `_run_critique` makes a synchronous Claude API call with 30-second timeout. Both block the async event loop.
- **Fix:** Wrap both in `await asyncio.to_thread(...)`.

### 8. Inconsistent Parameter Naming for Same Data
- **Source Agents:** pattern-recognition (P2), code-simplicity (P3), architecture (P3)
- **File:** research_agent/agent.py:216, :418, :515
- **Issue:** Same `self._critique_context` string passed as `critique_context` (decompose), `scoring_adjustments` (relevance), and `lessons_applied` (synthesize). Three different names obscure data lineage.
- **Fix:** Unify on `critique_guidance` across all stages.

### 9. Missing XML Boundaries in Relevance Scoring Prompt
- **Source Agent:** security-sentinel (P2)
- **File:** research_agent/relevance.py:136
- **Issue:** Critique context injected as bare `SCORING CONTEXT: {safe_adjustments}` without XML tags. Decompose uses `<critique_guidance>`, synthesize uses `<lessons_applied>`. Inconsistent with three-layer prompt injection defense.
- **Fix:** Wrap in `<scoring_guidance>` XML tags and reference in system prompt.

### 10. Second-Order Prompt Injection via Weakness Strings
- **Source Agent:** security-sentinel (P2)
- **File:** research_agent/context.py:218-219
- **Issue:** Weakness strings from YAML originate from previous Claude responses (which process web content). Attacker-crafted web content → Claude generates malicious weakness string → saved to YAML → loaded in future run → injected into prompts. Mitigated by 200-char truncation but chain of trust is long.
- **Fix:** Apply `sanitize_content()` to each individual weakness string before inserting into summary template.

### 11. Critique Context Not Registered in Token Budget
- **Source Agent:** performance-oracle (P2)
- **File:** research_agent/synthesize.py:481-490
- **Issue:** `lessons_applied` injected into synthesis prompt but not registered in `budget_components`. Adds unbounded tokens the budget pruner doesn't know about. Same for `scoring_adjustments` in relevance.
- **Fix:** Add to `budget_components` and `COMPONENT_PRIORITY` in `token_budget.py` at low priority.

### 12. `_critique_context` as Mutable Instance State
- **Source Agents:** architecture (P2), code-simplicity (P3)
- **File:** research_agent/agent.py:71
- **Issue:** Set at start of `_research_async`, read in `_evaluate_and_synthesize`. Only valid during a single call. Leaks between calls if agent is reused. Other context values are local variables.
- **Fix:** Pass as parameter through the call chain instead of storing on `self`.

### 13. `_last_critique` Stored but Never Read
- **Source Agent:** code-simplicity (P2)
- **File:** research_agent/agent.py:70, :151
- **Issue:** Set in `_run_critique` and initialized in `__init__` but never read by any production code. State stored for a hypothetical future feature.
- **Fix:** Remove `self._last_critique` and its assignment. (If agent-native P1 #2 is addressed by exposing via `research()` return value, this becomes moot.)

### 14. CritiqueResult Not in `research()` Return Value
- **Source Agent:** agent-native-reviewer (P2)
- **File:** research_agent/agent.py:164-166
- **Issue:** `research()` returns `str` (report text only). Programmatic consumers must reach into private `self._last_critique` to inspect quality.
- **Fix:** Return a `ResearchResult` dataclass with report text + optional `CritiqueResult`, or add a public `last_critique` property.

### 15. Tests Reimplement Agent Logic Instead of Testing It
- **Source Agents:** kieran-python (P2), code-simplicity (P2), pattern-recognition (P3)
- **File:** tests/test_critique.py:232-269
- **Issue:** `TestAgentCritiqueHistoryThreading` manually does `agent._critique_context = critique_ctx.content` instead of calling `_research_async`. Tests Python assignment, not agent behavior. Gives false confidence.
- **Fix:** Either test the actual async method with mocks, or extract critique loading into a testable helper.

### 16. `_summarize_patterns` Filtering Logic Confusing
- **Source Agents:** kieran-python (P2), pattern-recognition (P3)
- **File:** research_agent/context.py:176-225
- **Issue:** `load_critique_history` passes all valid critiques to `_summarize_patterns`, which internally filters to only passing ones. Docstring says "fewer than 3 valid critiques" but actually means "fewer than 3 valid **passing** critiques." Double filtering is confusing.
- **Fix:** Fix the docstring or pre-filter in `load_critique_history`.

### 17. Missing Docstring for `critique_context` Parameter
- **Source Agents:** kieran-python (P1), pattern-recognition (P3)
- **File:** research_agent/decompose.py:106-123
- **Issue:** `decompose_query` signature includes `critique_context: str | None = None` but the docstring's `Args:` block does not document it.
- **Fix:** Add the parameter to the docstring.

### 18. No `--no-critique` CLI Flag
- **Source Agent:** agent-native-reviewer (P2)
- **File:** research_agent/agent.py:135-136
- **Issue:** Quick mode skips critique (hardcoded), but there's no opt-out flag for standard/deep modes. Agents can't control cost or speed by skipping critique.
- **Fix:** Add `--no-critique` CLI flag.

### 19. Missing Plan Document in `docs/plans/`
- **Source Agent:** git-history-analyzer (P2)
- **File:** docs/plans/ (absent)
- **Issue:** Compound engineering workflow requires Brainstorm → Plan → Work → Review. A brainstorm exists but no plan. Work phase started without a formal plan, violating session discipline.
- **Fix:** Document this gap. Future features should follow the full loop.

### 20. Commit Size Convention Violated
- **Source Agent:** git-history-analyzer (P2)
- **File:** bad292e (460 lines), edc45f0 (334 lines)
- **Issue:** CLAUDE.md specifies 50-100 lines per commit. Two commits are 3-9x over. Regression from Cycle 17's discipline.
- **Fix:** Process improvement — future features should split large modules into smaller commits.

### 21. `query_domain` Machinery is YAGNI
- **Source Agent:** code-simplicity (P2)
- **File:** research_agent/context.py:230, research_agent/critique.py:56
- **Issue:** `load_critique_history` accepts a `domain` parameter but the only caller passes no domain filter. Entire domain extraction, storage, validation, and filtering machinery built for a hypothetical future use case.
- **Fix:** Remove `domain` parameter and `query_domain` field. Add later if needed.

### 22. Critique Saved Before Report Persisted
- **Source Agent:** data-integrity-guardian (P2)
- **File:** research_agent/agent.py:517-525
- **Issue:** Critique YAML saved before caller persists the report to disk. If report save fails, orphaned critique pollutes aggregate metrics.
- **Fix:** Acceptable for CLI tool. Consider saving critique as part of report save in `main.py` for stronger consistency.

### 23. Duplicated Dimension Constants Across Modules
- **Source Agent:** pattern-recognition (P2)
- **File:** research_agent/critique.py:25-30, research_agent/context.py:146-173
- **Issue:** Five critique dimensions listed independently in CritiqueResult fields, prompt template, YAML parser, and validation. Adding a dimension requires 4+ changes.
- **Fix:** Define in a single `CRITIQUE_DIMENSIONS` constant and derive fields/validation from it.

---

## P3 — Nice-to-Have

### 24. f-string in Logger Calls
- **Source Agents:** kieran-python, pattern-recognition, git-history
- **File:** research_agent/agent.py:156, research_agent/critique.py:203, research_agent/context.py:265-269
- **Fix:** Use lazy `%s` formatting for consistency.

### 25. Duplicate Scores Tuple in `CritiqueResult`
- **Source Agents:** kieran-python, pattern-recognition
- **File:** research_agent/critique.py:58-74
- **Fix:** Extract a private `_scores` property.

### 26. Double Sanitization of Critique Context
- **Source Agents:** code-simplicity, architecture
- **File:** research_agent/context.py:225, research_agent/decompose.py:140
- **Fix:** Sanitize once at source, remove downstream calls.

### 27. Timestamp Collision in Critique Filename
- **Source Agent:** data-integrity
- **File:** research_agent/critique.py:248-251
- **Fix:** Append short UUID suffix.

### 28. `bool` Bypasses `isinstance(val, int)` Validation
- **Source Agent:** data-integrity
- **File:** research_agent/context.py:156-159
- **Fix:** Add `isinstance(val, bool)` exclusion.

### 29. Quick Mode Loads Critique History Unnecessarily
- **Source Agent:** performance
- **File:** research_agent/agent.py:192-196
- **Fix:** Guard with `if self.mode.name != "quick":`.

### 30. Redundant Sanitize Calls Across Per-Source Scoring
- **Source Agent:** performance
- **File:** research_agent/relevance.py:133-136
- **Fix:** Pre-sanitize once in `evaluate_sources` before the per-source loop.

### 31. Critique Threshold Not Configurable
- **Source Agent:** agent-native
- **File:** research_agent/context.py:137
- **Fix:** Expose as parameter or field on `CycleConfig`.

### 32. Survivorship Bias in Pattern Summary (Design Note)
- **Source Agent:** data-integrity
- **File:** research_agent/context.py:182
- **Fix:** Consider adding separate "common weaknesses" summary from failing runs.

### 33. Various Test Quality Issues
- **Source Agents:** pattern-recognition, kieran-python
- **Files:** tests/test_relevance.py (duplicate fixtures, inconsistent asyncio marks), tests/test_decompose.py (duplicate TestLoadContext class), tests/test_critique.py (unused AsyncMock import)
- **Fix:** Clean up in a test hygiene pass.

### 34. Minor Code Tidiness
- **Source Agents:** kieran-python, code-simplicity, architecture, security
- **Files:** Various — `Counter[str]` annotation, `save_critique` directory validation, `mode_name`/`gate_decision` not sanitized, `_parse_critique_response` redundant truncation
- **Fix:** Address in a cleanup pass.

---

## Positive Findings (Consistent Across Agents)

These strengths were noted by multiple agents:

1. **Graceful degradation** — Critique never crashes the pipeline. Quick mode skips entirely. (architecture, code-simplicity, agent-native)
2. **Three-layer prompt injection defense** — sanitize_content + XML boundaries + system prompt applied consistently. (pattern-recognition, security, agent-native)
3. **YAML `safe_load` + schema validation** — Prevents code execution, validates data structure. Solid defense-in-depth. (data-integrity, security)
4. **Additive pattern compliance** — New module layers on without changing downstream modules. Mirrors skeptic.py integration pattern. (git-history, pattern-recognition)
5. **Frozen dataclass for CritiqueResult** — Consistent with ResearchMode, ResearchResult, ContextResult. (git-history)
6. **Structured YAML output** — Excellent for machine consumption. (agent-native)
7. **Self-improving feedback loop** — Past critiques influence future behavior. Novel agent-native pattern. (agent-native)
8. **Clean commit sequence** — Layered story (module → wiring → infrastructure → threading) is logical and reviewable. (git-history)
9. **Slug construction prevents path traversal** — `re.sub(r"[^a-z0-9_]", "", slug)` blocks directory traversal. (security)

---

## Statistics

| Severity | Count |
|----------|-------|
| P1 Critical | 4 |
| P2 Important | 19 |
| P3 Nice-to-have | 11 |
| **Total** | **34** |

## Agents & Batches

| Batch | Agents | Findings |
|-------|--------|----------|
| batch1 | kieran-python, pattern-recognition, code-simplicity | 15 + 14 + 15 = 44 raw |
| batch2 | architecture, security, performance | 9 + 8 + 11 = 28 raw |
| batch3 | data-integrity, git-history, agent-native | 7 + 4 + 7 = 18 raw |
| **Total raw** | | **90** |
| **After dedup** | | **34 unique** |

## Cross-Cutting Themes

The 34 findings cluster into **5 themes**:

1. **Agent observability gap** (P1 #2-4, P2 #14, #18) — The critique system works well internally but is invisible to external consumers. This is the highest-impact cluster.

2. **Convention regression** (P1 #1, P2 #19-20) — The `except Exception` anti-pattern was previously fixed. Commit sizes regressed from Cycle 17. Plan phase was skipped.

3. **Sync/async mismatch** (P2 #7) — Synchronous file I/O and API calls on the async event loop.

4. **Naming and consistency** (P2 #5, #8, #9, #23) — Hardcoded paths, inconsistent parameter names, inconsistent XML tag usage, duplicated dimension constants.

5. **Dead/premature code** (P2 #6, #13, #21) — CritiqueError never raised, _last_critique never read, query_domain unused.

## Recommended Fix Order

1. ~~**P1 #1** — Fix `except Exception`~~ ✅ batch 1
2. ~~**P1 #2-4** — CLI entry point, visible output, history read path~~ ✅ batch 1
3. ~~**P2 #5** — Extract `META_DIR` constant~~ ✅ batch 2
4. ~~**P2 #6** — Remove dead `CritiqueError`~~ ✅ batch 2
5. ~~**P2 #7** — Wrap in `asyncio.to_thread`~~ ✅ batch 2
6. ~~**P2 #8-9** — Unify parameter names + add XML tags~~ ✅ batch 2
7. ~~**P2 #10-11** — Sanitize weakness strings + register critique in token budget~~ ✅ batch 3
8. **P2 #12-13** — Remove mutable `_critique_context` state + dead `_last_critique` (10 min, simplification)
9. **P2 #14-15** — CritiqueResult in return value + fix test reimplementation (20 min, API + test quality)
10. **P2 #16-18** — Fix docstring, `--no-critique` flag, remaining cleanup (15 min)
11. Remaining P2s (#19-23) and P3s in cleanup passes

## Three Questions

1. **Hardest judgment call in this review?** Whether the agent-native findings (#2-4) are truly P1. They're feature requests rather than bugs — the code works correctly, it just lacks CLI surface area. I kept them P1 because agent accessibility is a core principle for this project, and a feature that agents can't observe or control is arguably incomplete.

2. **What did I consider flagging but chose not to, and why?** The code-simplicity reviewer's suggestion to remove critique threading from decompose and relevance (keeping only synthesize) was compelling but prescriptive. Whether upstream stages benefit from critique context is an empirical question, not a code quality issue. I left it as-is since it was an intentional design choice documented in the brainstorm.

3. **What might this review have missed?** No agent actually ran the test suite (`python3 -m pytest tests/ -v`). We reviewed test code but didn't verify all 558 tests pass with these changes. Additionally, no agent tested the actual critique output quality — whether Claude produces useful scores when given process metadata but never sees the report text.
