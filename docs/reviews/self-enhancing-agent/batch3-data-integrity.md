# Data Integrity Guardian — Review Findings

**PR:** Self-Enhancing Agent (self-critique feedback loop)
**Branch:** self-enhancing-agent (bad292e..57bf44e)
**Date:** 2026-02-23
**Agent:** data-integrity-guardian

## Findings

### Bare `except Exception` in `_run_critique`
- **Severity:** P2
- **File:** research_agent/agent.py:155
- **Issue:** `except (CritiqueError, Exception)` is redundant — `Exception` already covers `CritiqueError`. Violates project convention "Never bare `except Exception`." Swallows `TypeError`/`AttributeError` from coding mistakes, making bugs invisible.
- **Suggestion:** Narrow to `except (CritiqueError, StateError, OSError)` or at minimum use `logger.exception()` to preserve traceback.

### Timestamp collision in critique filename
- **Severity:** P3
- **File:** research_agent/critique.py:248-251
- **Issue:** `int(time.time())` has 1-second resolution. Two runs completing within the same second produce identical filenames; `atomic_write` rename silently overwrites the first, causing data loss.
- **Suggestion:** Append a short UUID suffix: `f"critique-{slug}_{timestamp}_{uuid.uuid4().hex[:6]}.yaml"`

### Hardcoded `Path("reports/meta")` in two places
- **Severity:** P2
- **File:** research_agent/agent.py:149 and :193
- **Issue:** Write path and read path are independent string literals. If CLI is invoked from a different working directory, writer saves to one location, reader looks in another — critique history silently empty forever. No single source of truth.
- **Suggestion:** Extract to a single constant `META_DIR = Path("reports/meta")` referenced by both call sites.

### Synchronous blocking I/O in async context
- **Severity:** P2
- **File:** research_agent/agent.py:193
- **Issue:** `load_critique_history()` performs synchronous file operations (glob, stat, read_text, yaml.safe_load) inside an async method. ~20+ blocking syscalls on the event loop with 10 YAML files. Could cause timeouts on slow filesystems.
- **Suggestion:** Wrap in `await asyncio.to_thread(load_critique_history, Path("reports/meta"))`.

### `bool` bypasses `isinstance(val, int)` validation
- **Severity:** P3
- **File:** research_agent/context.py:156-159
- **Issue:** `isinstance(True, int)` returns `True` in Python (bool subclasses int). YAML `source_diversity: true` parses as Python `True` (value 1), passing validation. Semantically incorrect data could skew pattern summaries.
- **Suggestion:** Add explicit bool exclusion: `if isinstance(val, bool) or not isinstance(val, int) or not (1 <= val <= 5):`

### Critique saved before report persisted (transaction boundary)
- **Severity:** P2
- **File:** research_agent/agent.py:517-525
- **Issue:** Sequence is: synthesize report → save critique → update gap states → return report string to caller (which saves to disk). If report save fails in the caller, an orphaned critique YAML exists referencing a run that never produced output. Pollutes aggregate quality metrics.
- **Suggestion:** Acceptable for CLI tool, but consider saving critique as part of the report save transaction in `main.py` for stronger consistency.

### YAML parsing safety (POSITIVE)
- **Severity:** N/A (positive finding)
- **File:** research_agent/context.py:263
- **Issue:** Correctly uses `yaml.safe_load()`, catches `yaml.YAMLError` and `OSError`, validates schema with `_validate_critique_yaml`. Solid defense-in-depth.
- **Suggestion:** No action needed.

### Survivorship bias in pattern summary (DESIGN NOTE)
- **Severity:** P3 (design note)
- **File:** research_agent/context.py:182
- **Issue:** `_summarize_patterns` only includes critiques where `overall_pass is True`. Failing runs (most informative for improvement) are excluded. Feedback loop optimizes for "maintain good quality" rather than "fix problems."
- **Suggestion:** Intentional design choice per brainstorm doc. Consider adding a separate "common weaknesses" summary from failing runs.

## Summary
- P1 (Critical): 0
- P2 (Important): 4
- P3 (Nice-to-have): 3
