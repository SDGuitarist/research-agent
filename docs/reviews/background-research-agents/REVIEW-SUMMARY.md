# Code Review Summary

**PR:** Background research agents: queue/digest skills + context system refactor
**Branch:** feat/background-research-agents (merged to main, commits 52e32bf..aae39bb)
**Date:** 2026-02-26
**Agents Used:** kieran-python-reviewer, pattern-recognition-specialist, code-simplicity-reviewer, architecture-strategist, security-sentinel, performance-oracle, data-integrity-guardian, git-history-analyzer, agent-native-reviewer

## Prior Review Context

Todos 054-063 were created from an earlier review round and are all marked **done**. This synthesis covers only **new findings** from the full 9-agent review, after deduplication.

---

## P1 — Critical (Blocks Merge)

### 1. ValueError from resolve_context_path uncaught in CLI and public API
- **Source Agents:** kieran-python-reviewer (P1), agent-native-reviewer (P2)
- **Files:** `research_agent/cli.py:311-318`, `research_agent/__init__.py:99-102`
- **Issue:** `resolve_context_path()` raises `ValueError` for path traversal attempts (names with `/`, `\`, or leading `.`), but the CLI only catches `FileNotFoundError`. A user typing `--context ../evil` gets an unhandled Python traceback. Same issue in the public API — `ValueError` propagates as an unexpected exception instead of `ResearchError`.
- **Fix (CLI):** Change `except FileNotFoundError` to `except (FileNotFoundError, ValueError)` with clean stderr output.
- **Fix (API):** Wrap in try/except converting to `ResearchError`.

### 2. Double-sanitization produces `&amp;amp;` in reports
- **Source Agents:** performance-oracle (P2), security-sentinel (P1, architectural)
- **Files:** `research_agent/synthesize.py:132,441`
- **Issue:** Context content goes through `sanitize_content()` at each consumer (synthesize_draft and synthesize_final). Since `sanitize_content()` replaces `&` with `&amp;`, double-sanitization produces `&amp;amp;` — a data corruption bug visible in deep mode reports where both draft and final pass process the same context. Any `&` in context files (e.g., "R&D") appears as `&amp;` in the final report.
- **Fix:** Sanitize context content once at load time in `load_full_context()`. Remove redundant `sanitize_content(context)` calls in consumers. Related to P2 finding #1 below.

---

## P2 — Important (Should Fix)

### 1. Context content sanitized per-consumer, not at load boundary
- **Source Agents:** security-sentinel (P1 architectural), performance-oracle (P2)
- **File:** `research_agent/context.py:84-97`
- **Issue:** `load_full_context()` returns raw file content. Sanitization happens at 4+ call sites: `synthesize_draft()`, `synthesize_final()`, `decompose_query()`, `skeptic.py`. Any new consumer that forgets to sanitize creates a prompt injection vector. All current consumers sanitize correctly — the risk is architectural (future consumers).
- **Fix:** Sanitize at load time in `load_full_context()` right after `content = path.read_text().strip()`. Remove redundant calls in consumers. This also fixes P1 #2 above.

### 2. Path traversal defense uses string prefix instead of `is_relative_to`
- **Source Agents:** kieran-python-reviewer (P1), pattern-recognition-specialist (P2), data-integrity-guardian (P3)
- **File:** `research_agent/context.py:54-58`
- **Issue:** Defense layer 2 uses `str(path).startswith(str(contexts_resolved) + "/")`. The standard Python idiom `path.is_relative_to()` (3.9+) handles edge cases like case-insensitive filesystems (macOS APFS). Layer 1 blocks all realistic attacks, so this is defense-in-depth hardening.
- **Fix:** Replace with `path.is_relative_to(contexts_resolved)`.
- **Note:** Previous todo 054 implemented the current fix; this is a refinement.

### 3. Module-level context cache (thread safety, size, test pollution)
- **Source Agents:** kieran-python (P2), pattern-recognition (P3), code-simplicity (P2), architecture (P2), data-integrity (P2), performance (P2) — **6 agents flagged this**
- **File:** `research_agent/context.py:23`
- **Issue:** `_context_cache` is a module-level dict with no thread safety, no size bound, and no eviction. In concurrent use (public API supports async), `clear_context_cache()` cross-contaminates between instances. In long-running processes, cache grows unbounded. Tests depend on `tmp_path` uniqueness to avoid pollution.
- **Fix:** Move cache to `ResearchAgent` instance, or add `functools.lru_cache(maxsize=32)`.

### 4. Public API accesses private attributes
- **Source Agents:** kieran-python-reviewer (P2), pattern-recognition-specialist (P2)
- **File:** `research_agent/__init__.py:113-114`
- **Issue:** `run_research_async()` reads `agent._last_source_count` and `agent._last_gate_decision` — underscore-prefixed private attributes. Couples public API to internal implementation.
- **Fix:** Add public read-only properties to `ResearchAgent` (like existing `last_critique` property).

### 5. Auto-detect LLM call adds 1-3s latency to every run
- **Source Agents:** performance-oracle (P1)
- **File:** `research_agent/agent.py:226-236`
- **Issue:** When no `--context` flag given and `contexts/` exists, `auto_detect_context()` makes a Sonnet API call. Adds 1-3s before research begins. Uses full Sonnet for a trivial classification task.
- **Fix:** (a) Use Haiku for auto-detection. (b) Short-circuit when `contexts/` has exactly one `.md` file. (c) Cache result per query hash.

### 6. Context block building duplicated across 3 files
- **Source Agents:** pattern-recognition-specialist (P2)
- **Files:** `research_agent/synthesize.py:167-175,456-464`, `decompose.py:90-97`, `skeptic.py:42-47`
- **Issue:** The `<research_context>` XML block building pattern is copy-pasted in 4 places across 3 files. `skeptic.py` has a clean `_build_context_block()` helper, but other modules don't use it.
- **Fix:** Extract shared helper into `sanitize.py` or `prompt_helpers.py`.

### 7. Non-atomic file writes in CLI output path
- **Source Agents:** data-integrity-guardian (P2)
- **File:** `research_agent/cli.py:350`
- **Issue:** CLI saves reports with `Path.write_text()`, not atomic. Background agents writing via `-o` are vulnerable — a partial file passes the queue skill's existence check and gets marked Completed with a corrupted report. `safe_io.atomic_write()` already exists in the codebase.
- **Fix:** Replace `output_path.write_text(report)` with `atomic_write(output_path, report)`.

### 8. API parity gaps — 6 CLI features not exposed programmatically
- **Source Agents:** agent-native-reviewer (P2)
- **File:** `research_agent/__init__.py`
- **Issue:** Agents using the Python API cannot: list reports (`--list`), critique reports (`--critique`), view critique history (`--critique-history`), skip critique (`--no-critique`), override source count (`--max-sources`), or append to research log. Functions exist internally but are not exported.
- **Fix:** Export `list_reports()`, `critique_report_file`, `load_critique_history` in `__init__.py.__all__`. Add `skip_critique` and `max_sources` params to `run_research()`.
- **Note:** 4 of these gaps are pre-existing (not introduced by this PR) but now more visible.

### 9. `load_full_context` FAILED status silently drops to no-context
- **Source Agents:** architecture-strategist (P2)
- **File:** `research_agent/context.py:98-100`
- **Issue:** When an `OSError` occurs reading a context file, `load_full_context()` returns `ContextResult.failed()`. The `__bool__` returns `False` for FAILED, so it's treated identically to NOT_CONFIGURED. A context file with permissions errors is silently treated as "no context."
- **Fix:** Check `result.status == ContextStatus.FAILED` in agent and log a user-visible warning.

### 10. `_last_critique` not reset between runs
- **Source Agents:** pattern-recognition-specialist (P2)
- **File:** `research_agent/agent.py:79-84,214-218`
- **Issue:** Six mutable run-state attributes are reset at top of `_research_async()`, but `_last_critique` is missing from the reset block. Set at line 179, never cleared. A second run that doesn't produce a critique will report the first run's critique via `last_critique` property.
- **Fix:** Add `self._last_critique = None` to the reset block.

### 11. Test patches may miss CONTEXTS_DIR mock
- **Source Agents:** code-simplicity-reviewer (P2)
- **File:** `tests/test_agent.py:260`
- **Issue:** Standard/deep mode tests patch `load_full_context` but don't mock `CONTEXTS_DIR.is_dir()`, so they depend on real filesystem. Since `contexts/pfe.md` exists in the repo, these tests could trigger real auto-detect API calls.
- **Fix:** Add `patch("research_agent.agent.CONTEXTS_DIR")` with `mock_ctx_dir.is_dir.return_value = False` to non-auto-detect test fixtures.

### 12. Auto-detect fallback silently kills legacy default context
- **Source Agents:** code-simplicity-reviewer (P2)
- **File:** `research_agent/agent.py:233-236`
- **Issue:** When `auto_detect_context` returns `None`, the code sets `effective_no_context = True` with source `"--context none"`. This is misleading (user didn't pass `--context none`) and prevents `load_full_context()` from falling back to the legacy `research_context.md` default.
- **Fix:** Fix source string to `"auto-detect: no match"`. Document whether `contexts/` replaces the legacy default.

### 13. Queue skill shell escaping is LLM prose, not code-enforced
- **Source Agents:** security-sentinel (P2)
- **File:** `.claude/skills/research-queue/SKILL.md:153-162`
- **Issue:** Shell escaping (sanitize, replace control chars, escape quotes, wrap in single quotes) is described as prose instructions for the LLM. A crafted query in `queue.md` could theoretically manipulate the LLM to bypass escaping.
- **Fix:** Extract shell sanitization into a Python utility function, or add a `--from-queue` CLI flag that handles its own sanitization.

### 14. Skill file hardcodes absolute path
- **Source Agents:** kieran-python-reviewer (P3), architecture-strategist (P2)
- **File:** `.claude/skills/research-queue/SKILL.md:174`
- **Issue:** Hardcodes `/Users/alejandroguillen/Projects/research-agent` — non-portable and leaks personal info.
- **Fix:** Use `pwd` or a placeholder.

### 15. `run_research_async` context resolution duplicates CLI logic
- **Source Agents:** code-simplicity-reviewer (P2)
- **File:** `research_agent/__init__.py:96-106`
- **Issue:** Same 6-line `resolve_context_path` → check None → set `no_context` pattern repeated in both `__init__.py` and `cli.py`.
- **Fix:** Extract shared `resolve_context_args(context_name) -> tuple[Path | None, bool]`.

### 16. daily_spend.json budget resets on corruption
- **Source Agents:** security-sentinel (P2)
- **File:** `.claude/skills/research-queue/SKILL.md:105-115`
- **Issue:** If `daily_spend.json` is corrupted or deleted, skill recreates it with `$0.00` spent, effectively bypassing the daily budget limit. Not a security boundary (budget is a guardrail) but could allow unintended overspend.
- **Fix:** When recreating, estimate `total_spent` from completed/failed items in `queue.md`.

### 17. Four-way section_list branching in synthesize_final
- **Source Agents:** code-simplicity-reviewer (P2)
- **File:** `research_agent/synthesize.py:509-540`
- **Issue:** Branches on two booleans (context × skeptic_findings), producing 4 nearly-identical 32-line string blocks. Only differences are which sections are included and numbering.
- **Fix:** Build section list incrementally with conditional appends.

---

## P3 — Nice-to-Have

### 1. `auto_detect_context` "none" parsing too permissive
- **Source:** kieran-python-reviewer
- **File:** `research_agent/context.py:186`
- Strip quotes before checking for "none".

### 2. Exception handling tuple order inconsistency
- **Source:** pattern-recognition-specialist
- **Files:** `context.py:180`, `decompose.py:158`, `api_helpers.py:56`
- Define `ANTHROPIC_API_ERRORS` tuple in `errors.py`.

### 3. Overlapping constructor params (context_path + no_context)
- **Source:** code-simplicity-reviewer
- **File:** `research_agent/agent.py:66-67`
- Consider unified `context: Path | None | Literal["none"]` in next version.

### 4. `_load_context_for` trivial wrapper
- **Source:** kieran-python-reviewer, code-simplicity-reviewer
- **File:** `research_agent/agent.py:91-100`
- Inline at call site and delete.

### 5. ContextResult uses quoted forward reference instead of `Self`
- **Source:** kieran-python-reviewer
- **File:** `research_agent/context_result.py:39,50,55,60`
- Use `from typing import Self` (Python 3.14).

### 6. `synthesize_report` docstring missing `context` parameter
- **Source:** pattern-recognition-specialist
- **File:** `research_agent/synthesize.py:89-120`

### 7. Deep mode `synthesis_instructions` references `<research_context>` redundantly
- **Source:** architecture-strategist
- **File:** `research_agent/modes.py:154-157`

### 8. CLAUDE.md says "three-way" for four-state ContextResult
- **Source:** architecture-strategist
- **File:** `CLAUDE.md`
- Update to "Four-way context result (loaded/empty/not_configured/failed)."

### 9. `auto_detect_context` uses sync client (could use async)
- **Source:** code-simplicity-reviewer
- **File:** `research_agent/agent.py:227-229`, `context.py:131-199`

### 10. `_build_sources_context` called twice with same data (draft + final)
- **Source:** performance-oracle
- **File:** `research_agent/synthesize.py`
- Pass `sources_text` from draft to final.

### 11. `_build_sources_context` stores full strings for dedup
- **Source:** performance-oracle
- **File:** `research_agent/synthesize.py:636-667`
- Use hash-based dedup instead.

### 12. Token budget uses 4 chars/token approximation
- **Source:** performance-oracle
- **File:** `research_agent/token_budget.py:12-23`
- Adjust to 3.5 or use SDK tokenizer.

### 13. URL attribute not sanitized in `_build_sources_context`
- **Source:** security-sentinel
- **File:** `research_agent/synthesize.py:660-664`

### 14. Queue skill stagger delay wastes 15 seconds
- **Source:** performance-oracle
- **File:** `.claude/skills/research-queue/SKILL.md:170-171`
- Reduce to 3-5 seconds.

### 15. Plan deepened after implementation (process inversion)
- **Source:** git-history-analyzer
- Informational — consider deeper initial planning for future features.

### 16. Tests added separately from security fixes
- **Source:** git-history-analyzer
- Minor process observation.

### 17. Research log append is CLI-only
- **Source:** agent-native-reviewer
- **File:** `research_agent/cli.py:48-67`

### 18. f-string logging inconsistency
- **Source:** kieran-python-reviewer, pattern-recognition-specialist
- Already tracked in `todos/050-pending-p3-fstring-logging.md`.

### 19. synthesize_draft duplicated string literals
- **Source:** code-simplicity-reviewer
- **File:** `research_agent/synthesize.py:291-325`
- Related to P2 #17 (four-way branching).

---

## Statistics

| Severity | Count |
|----------|-------|
| P1 Critical | 2 |
| P2 Important | 17 |
| P3 Nice-to-have | 19 |
| **Total** | **38** |

*After deduplication across 9 agents. Raw finding count before dedup: ~55.*

## Agents & Batches

| Batch | Agents | Raw Findings | After Dedup |
|-------|--------|--------------|-------------|
| batch1 | kieran-python, pattern-recognition, code-simplicity | 27 | 20 |
| batch2 | architecture, security, performance | 19 | 13 |
| batch3 | data-integrity, git-history, agent-native | 11 | 5 |

## Cross-Agent Agreement (Findings Flagged by 3+ Agents)

| Finding | Agents | Final Severity |
|---------|--------|---------------|
| Module-level context cache | 6 agents | P2 |
| Path traversal string prefix | 3 agents | P2 |
| Private attribute access from public API | 2 agents | P2 |
| Context sanitization architecture | 2 agents | P2 |
| Double-sanitization bug | 2 agents | P1 |

## Positive Patterns (Consensus)

The 9 agents identified several strong patterns in this PR:

1. **Single-writer architecture** — main session is sole writer to queue.md and daily_spend.json
2. **Running state elimination** — no limbo items on crash
3. **Layered refactoring** — subtract before adding (context.py went through 5 clean evolutionary steps)
4. **Defense-in-depth path traversal** — two independent validation layers
5. **ContextResult frozen dataclass** — immutable state, factory methods with invariants
6. **Local variables for async safety** — preserves agent reuse
7. **Additive pipeline pattern** — new stages layer on without changing downstream
8. **Specific exception handling** — no bare `except Exception` anywhere
9. **Sub-agent delegation in digest** — respects context budget
10. **Context system agent-native design** — `list_available_contexts()`, `resolve_context_path()`, auto-detect all exported

## Three Questions

1. **Hardest judgment call in this review?** The double-sanitization finding (#P1-2). The performance-oracle flagged it as P2 (redundant work), but realizing `sanitize_content` is not idempotent (`&` → `&amp;` → `&amp;amp;`) upgrades it to P1 data corruption. The security-sentinel saw the architectural risk of per-consumer sanitization but framed it as future risk, not current bug. Combining both perspectives reveals it's both: an active bug (double-encoding) AND an architectural smell (sanitize at boundary, not per-consumer). Fixing the architecture also fixes the bug.

2. **What did you consider flagging but chose not to, and why?** The `synthesize_draft` two large duplicated string literals (P3 #19). Three agents flagged related code (section branching, implicit numbering, duplicated literals) — all pointing at the same ~60 lines in synthesize.py. I consolidated into P2 #17 (the clearest fix) and left the rest as P3 informational rather than creating 3 overlapping todos.

3. **What might this review have missed?** The skills (.claude/skills/*.md) are prose instructions, not executable code — they can't be tested by pytest or statically analyzed. Six of the 9 agents treated them as code review targets, but their "bugs" are really prompt engineering risks (LLM might misinterpret escaping instructions, might skip validation steps). The actual runtime behavior depends on Claude Code's interpretation. A live integration test of `/research:queue` with adversarial queue content would be more valuable than code review for these files.
