# Performance Oracle — Review Findings

**PR:** Background research agents: queue/digest skills + context system refactor
**Branch:** main (52e32bf..aae39bb)
**Date:** 2026-02-26
**Agent:** performance-oracle

## Findings

### Auto-detect LLM call adds 1-3s latency to every run
- **Severity:** P1
- **File:** research_agent/agent.py:226-236
- **Issue:** When no `--context` flag given and `contexts/` exists, `auto_detect_context()` makes a synchronous Claude Sonnet API call (wrapped in `asyncio.to_thread`). Adds 1-3 seconds before any research begins. Uses full Sonnet for what is essentially a trivial classification task.
- **Suggestion:** (a) Use Haiku for auto-detection (classification task, ~0.3s vs ~2s). (b) Short-circuit when `contexts/` has exactly one `.md` file — no LLM call needed. (c) Cache auto-detect result per query hash to disk.

### list_available_contexts reads every file on every auto-detect call
- **Severity:** P1
- **File:** research_agent/context.py:109-128
- **Issue:** Reads full text of every `.md` file in `contexts/` on every call, then truncates to 5 lines. Not cached — `clear_context_cache()` runs at start of each research run, and `list_available_contexts` doesn't use `_context_cache` anyway.
- **Suggestion:** Read only first 1024 bytes per file instead of full contents. Cache previews since context files change rarely.

### Module-level _context_cache has no size bound or eviction
- **Severity:** P2
- **File:** research_agent/context.py:23
- **Issue:** No maximum size on cache dict. In a long-running process (MCP server), cache grows without bound. Each entry stores full file content as string.
- **Suggestion:** Replace with `functools.lru_cache(maxsize=32)` or add max-size check.

### _build_sources_context dedup stores full strings in set
- **Severity:** P2
- **File:** research_agent/synthesize.py:636-667
- **Issue:** Deduplication normalizes each summary with `" ".join(text.split())` and stores full normalized string in a set. For deep mode with 60 chunks, this stores 60 copies of summary text purely for dedup.
- **Suggestion:** Use hash-based dedup: `seen: set[int] = set()` with `hash(normalized)`.

### sanitize_content called redundantly on same data
- **Severity:** P2
- **File:** research_agent/synthesize.py:132,441
- **Issue:** Context content goes through `sanitize_content()` twice in standard/deep path. Since `sanitize_content` replaces `&` with `&amp;`, double-sanitization produces `&amp;amp;` — a double-encoding bug.
- **Suggestion:** Sanitize context once at load time in `load_full_context()`. Remove redundant calls.

### Queue skill stagger delay wastes 15 seconds
- **Severity:** P2
- **File:** .claude/skills/research-queue/SKILL.md:170-171
- **Issue:** Hardcoded `sleep 15` between launching background agents. Fixed delay regardless of API conditions. Pipeline already has internal rate limiting (semaphore, batch backoff).
- **Suggestion:** Reduce to 3-5 seconds or remove entirely, relying on pipeline-internal rate limiting.

### Token budget uses 4 chars/token approximation
- **Severity:** P3
- **File:** research_agent/token_budget.py:12-23
- **Issue:** `count_tokens()` uses `len(text) // 4`. Actual English ratio is ~3.5 chars/token, so system over-counts by ~15%, pruning content earlier than necessary. The Anthropic SDK may include a local tokenizer.
- **Suggestion:** Adjust ratio to 3.5 or use SDK's local token counter if available. Low priority — over-counting is conservative.

### _summarize_patterns iterates critiques multiple times
- **Severity:** P3
- **File:** research_agent/context.py:238-292
- **Issue:** Iterates `passing_critiques` three times: dimension averages, weakness counting, pre-filter. With max 10 critiques, this is negligible.
- **Suggestion:** No action needed for 10 items.

### _build_sources_context called twice with same data
- **Severity:** P3
- **File:** research_agent/synthesize.py (draft and final paths)
- **Issue:** Same function called in both `synthesize_draft()` and `synthesize_final()` with identical summaries list, rebuilding the same string.
- **Suggestion:** Pass `sources_text` from draft through to final instead of rebuilding.

### Digest skill sub-agent model choice is correct (positive)
- **Severity:** P3 (positive)
- **File:** .claude/skills/research-digest/SKILL.md:56
- **Issue:** Correctly uses Haiku sub-agents for report reading. Each reads ~2000-3500 words and returns ~100 words. Efficient design.
- **Suggestion:** No change needed.

## Summary
- P1 (Critical): 2
- P2 (Important): 4
- P3 (Nice-to-have): 4
