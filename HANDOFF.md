# Handoff: Todo Fixes — P1, P2, P3 Batch

## Current State

**Project:** Research Agent
**Phase:** Work (fixing review todos on main)
**Branch:** `main`
**Date:** February 26, 2026

---

## What Was Done This Session

Fixed 8 todos across P1/P2/P3 priorities in 7 commits (`20319b7..dabbba7`):

### P1 Fixes
| Commit | Todo | Fix |
|--------|------|-----|
| `20319b7` | 064 | Catch `ValueError` from `resolve_context_path` in CLI and public API |
| `76f0471` | 065 | Sanitize context once at load time, remove redundant consumer calls |

### P2 Fixes
| Commit | Todo | Fix |
|--------|------|-----|
| `998290d` | 071 | Use `Path.is_relative_to` instead of string prefix check |
| `c4716e0` | 074 | Reset `_last_critique` between runs |
| `92d2978` | 067 | Use `atomic_write` for CLI report output |

### P3 Fixes
| Commit | Todo | Fix |
|--------|------|-----|
| `1d0b121` | 050+052 | %-style logging in coverage.py + named `MAX_TRIED_OVERLAP` constant |
| `dabbba7` | 053 | Extract `_collect_tried_queries` helper, remove duplication |

All 712 tests passing throughout. All commits pushed to `origin/main`.

### Remaining Pending Todos

**P2 (6 remaining):**
- 066: Module-level context cache thread safety (Medium)
- 068: API parity gaps — 6 CLI features not exposed (Medium)
- 069: Auto-detect LLM call latency — use Haiku (Small-Medium)
- 070: Context block building duplicated across 3 files (Small)
- 072: Public API accesses private `_` attributes (Small)
- 073: FAILED context silently drops to no-context (Small)

**P3 (3 remaining):**
- 061: `list_available_contexts` reads entire files for preview (Small)
- 062: Stale "business context" in docstrings (Small)
- 063: Auto-detect prompt fragility — verbose LLM responses (Small)

## Three Questions

1. **Hardest implementation decision in this session?** The double-sanitization fix (065) — deciding to move sanitization to load time and update all consumers + their tests, rather than making `sanitize_content` idempotent. Load-time sanitization is the cleaner architectural boundary.

2. **What did you consider changing but left alone, and why?** Considered also fixing the f-string logger calls in `query_validation.py` when fixing 050 in `coverage.py`. Left it alone because the todo only scoped coverage.py, and scope creep across modules risks unintended side effects.

3. **Least confident about going into the next batch?** The 11 "pending" todos that are actually `status: done` (045-049, 055-060) have misleading filenames containing "pending". Could cause confusion in future sessions scanning by filename.

## Next Phase

Continue fixing remaining todos, or proceed to **review** of the background research agents feature.

### Prompt for Next Session

```
Read todos/061-pending-p3-full-file-read-preview.md, todos/062-pending-p3-stale-business-context-docstrings.md, and todos/063-pending-p3-auto-detect-prompt-fragility.md. Fix all three P3s. Relevant files: research_agent/context.py, research_agent/synthesize.py, tests/test_context.py, tests/test_agent.py. Run tests after each fix. Commit each fix separately. After all commits, push and say DONE.
```
