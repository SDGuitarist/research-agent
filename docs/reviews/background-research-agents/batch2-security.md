# Security Sentinel — Review Findings

**PR:** Background research agents: queue/digest skills + context system refactor
**Branch:** main (52e32bf..aae39bb)
**Date:** 2026-02-26
**Agent:** security-sentinel

## Findings

### Context file content sanitized per-consumer, not at load boundary
- **Severity:** P1
- **File:** research_agent/context.py:84-97
- **Issue:** `load_full_context()` returns raw file content. Sanitization happens at each consumer: `synthesize_report()` line 132, `synthesize_final()` line 441, `decompose_query()` line 92. This means any new consumer of `_run_context.content` that forgets to sanitize creates a prompt injection vector. A malicious context file with `</research_context>` tags could escape its XML boundary. All current consumers sanitize correctly — the risk is architectural (future consumers).
- **Suggestion:** Sanitize at load time in `load_full_context()` right after `content = path.read_text().strip()`. Remove redundant `sanitize_content(context)` calls in consumers. Since `sanitize_content()` is not idempotent (`&` → `&amp;` → `&amp;amp;`), sanitize exactly once at the boundary.

### Queue skill shell command construction is LLM-interpreted, not code-enforced
- **Severity:** P2
- **File:** .claude/skills/research-queue/SKILL.md:153-162
- **Issue:** Shell escaping (strip whitespace, replace control chars, limit length, escape single quotes via `'\''`, wrap in single quotes) is described as prose instructions to the LLM. LLMs can misinterpret or skip steps under adversarial prompt conditions. A crafted query in `queue.md` could manipulate the LLM executing the skill to bypass escaping.
- **Suggestion:** Extract shell sanitization into a Python utility function, or add a `--from-queue` CLI flag that accepts a queue item index (letting `cli.py` handle its own sanitization).

### subprocess.run path could bypass symlink extension check
- **Severity:** P2
- **File:** research_agent/cli.py:357
- **Issue:** `subprocess.run(["open", "-t", str(output_path)])` checks `.suffix != ".md"` on the logical path, not the resolved target. An `output_path` that is a symlink to a non-`.md` file would pass the extension check. Practical risk is low (local CLI, user controls their machine).
- **Suggestion:** Add `output_path = output_path.resolve()` before the subprocess call and re-verify the extension. Add a comment noting `shell=False` is intentional.

### daily_spend.json budget file resets on corruption
- **Severity:** P2
- **File:** .claude/skills/research-queue/SKILL.md:105-115
- **Issue:** If `daily_spend.json` is corrupted or deleted, the skill recreates it with `total_spent: 0.00`, effectively bypassing the daily budget limit. The user could also hand-edit to reduce spent amount. The `reports/` directory is gitignored so there's no version control protection. Practical risk: budget is a guardrail against accidental overspending, not a security boundary.
- **Suggestion:** When recreating a corrupt file, estimate `total_spent` from completed/failed items in `queue.md` (they include cost annotations). Use `atomic_write()` from `safe_io.py` to prevent corruption from partial writes.

### Context file name unsanitized in auto-detect prompt
- **Severity:** P3
- **File:** research_agent/context.py:157-159
- **Issue:** Context file name included in LLM prompt without sanitization. A file named `</query>ignore above` could inject into prompt structure. Practical risk very low (local filesystem, response validated against allowlist).
- **Suggestion:** Apply `sanitize_content()` to the name for consistency.

### URL attribute not sanitized in _build_sources_context
- **Severity:** P3
- **File:** research_agent/synthesize.py:660-664
- **Issue:** URLs embedded in XML prompt structure (`<url>{url}</url>`) without sanitization. Title and summary are sanitized. A crafted URL with `</url></source>` could break XML structure. Risk low (URLs from Tavily/DuckDuckGo, validated by SSRF checks).
- **Suggestion:** Apply `sanitize_content(url)` when embedding in XML prompts.

### Digest skill path validation is prose, not code
- **Severity:** P3
- **File:** .claude/skills/research-digest/SKILL.md:46-51
- **Issue:** Four-step path validation including symlink check described as instructions for LLM to follow, not deterministic code. Primary defense is that queue skill controls both writing and reading of paths.
- **Suggestion:** Accept as-is. If path validation becomes critical, extract into a Python function.

## Summary
- P1 (Critical): 1
- P2 (Important): 3
- P3 (Nice-to-have): 3
