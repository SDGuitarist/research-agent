# HANDOFF — Research Agent

**Date:** 2026-03-08
**Branch:** `main`
**Phase:** Fix COMPLETE — next phase is Compound

## Current State

Cycle 24 (Swappable Context Profiles) review fixes applied. All 4 findings from `docs/reviews/2026-03-06-cycle-24-codex-findings.md` resolved.

Full suite result: `python3 -m pytest tests/ -v` -> `938 passed in 140.94s` (18 new tests).

## What Was Done

### Fix 1: Blocked domains leak into query refinement (P2 blocker)
- Added early `filter_blocked_urls()` call in `_research_with_refinement()` BEFORE `seen_urls` and `snippets` are built (agent.py ~line 969)
- Added same early filter in `_research_deep()` BEFORE `seen_urls` is built (agent.py ~line 1045)
- The existing filter in `_fetch_extract_summarize()` remains as defense-in-depth

### Fix 2: `--list-contexts` hides malformed frontmatter (P2 advisory)
- Added heuristic in cli.py: if file has `---` frontmatter markers but both template and profile are None, display `(frontmatter parse error)` instead of `no profile fields`
- Changed `OSError` catch message from `(parse error)` to `(read error)` for clarity

### Fix 3: Free-text tone double-sanitized (P3 advisory)
- Removed `sanitize_content()` call from `_build_tone_instruction()` in synthesize.py
- Tone is already sanitized at parse time in context.py — applying it again would double-escape `&`, `<`, `>`

### Fix 4: Missing focused regression tests (P3 advisory)
- Added 7 tests in `TestFilterBlockedUrls` (test_search.py): exact match, subdomain, similar domain, empty list, malformed URL, port, mixed results
- Added 7 tests in `TestBuildToneInstruction` (test_synthesize.py): preset expansion, case-insensitive, free-text, empty, whitespace, no double-sanitize, truncation
- Added 4 tests in `TestParseTemplateFrontmatterDetection` (test_context.py): malformed YAML, valid no-profile, no frontmatter, CLI heuristic distinction

## Three Questions

1. **Hardest fix in this batch?** The blocked-domain leak (fix 1). The filter already existed in `_fetch_extract_summarize()`, but the issue was that `_research_with_refinement()` uses results BEFORE that filter runs — for `seen_urls` (dedup) and `snippets` (which feed `refine_query()`). Adding early filtering in both `_research_with_refinement()` and `_research_deep()` means blocked domains are now filtered twice (early + in `_fetch_extract_summarize`), but `filter_blocked_urls` is a no-op on already-filtered results, so this is harmless defense-in-depth.

2. **What did you consider fixing differently, and why didn't you?** Considered removing the filter from `_fetch_extract_summarize()` now that early filtering exists, but keeping it provides defense-in-depth — any future search path that bypasses the early filter still gets caught.

3. **Least confident about going into the next batch or compound phase?** The `--list-contexts` parse error heuristic (fix 2). It works because malformed YAML returns `body == raw` (frontmatter not stripped), but a file with valid YAML frontmatter containing ONLY unrecognized keys (no template, no profile fields) would also show as `(frontmatter parse error)`. This is actually the correct behavior — such a file IS misconfigured — but it's worth noting.

### Prompt for Next Session

```
Read HANDOFF.md. Run the compound phase for Cycle 24 (Swappable Context Profiles). Write a solution doc in docs/solutions/ and run /update-learnings.
```
