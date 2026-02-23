# Fix Batch 3: P2 Findings #10-11

**Commit:** `fix(critique): resolve P2 review findings #10-11`
**Files changed:** `research_agent/context.py`, `research_agent/relevance.py`, `research_agent/synthesize.py`, `research_agent/token_budget.py`, `tests/test_context.py`, `tests/test_token_budget.py`
**Tests:** 605 passed

## Prior Phase Risk

> "The `asyncio.to_thread` wrapping of `_run_critique` — it passes `self` method plus keyword args through the thread boundary. This works because `_run_critique` only reads `self.client` (thread-safe Anthropic client) and writes `self._last_critique` (no concurrent readers). But if future code reads `_last_critique` concurrently, this could race."

Accepted: This batch doesn't touch async threading. The next batch (#12-13) removes `_last_critique` entirely, which eliminates the race risk.

## Fixes Applied

### P2 #10: Second-Order Prompt Injection via Weakness Strings (context.py:218)
- Applied `sanitize_content()` to each individual weakness string before inserting into the summary template
- Attack chain was: attacker web content → Claude generates malicious weakness string → saved to YAML → loaded in future run → injected into prompts
- The 200-char truncation in `_validate_critique_yaml` limits blast radius, but sanitization closes the gap
- Added test: `test_weakness_strings_are_sanitized` — verifies XML tags are stripped from weakness strings while preserving the legitimate text

### P2 #11: Critique Context Not Registered in Token Budget (synthesize.py, relevance.py, token_budget.py)
- Added `"critique_guidance": 2` to `COMPONENT_PRIORITY` (pruned after staleness_metadata, before previous_baseline)
- Renumbered existing priorities: previous_baseline→3, gap_schema→4, business_context→5, sources→6, instructions→7
- `NEVER_PRUNE_THRESHOLD` derives dynamically from `COMPONENT_PRIORITY["instructions"]` — no hardcoded update needed
- In `synthesize_final`: added critique_guidance to `budget_components` dict before budget pruning; read back potentially truncated value after pruning
- In `_apply_budget_pruning`: added generic `elif name in components` handler that truncates any pruned component via the mutable components dict — avoids adding a new parameter/return value per component
- In `relevance.py` (`score_source`): capped critique_guidance at 500 tokens via `truncate_to_budget` — scoring prompts are small per-source so full budget system is overkill
- Updated priority ordering test to include critique_guidance and new instructions value (7)

## Three Questions

1. **Hardest fix in this batch?** The token budget registration (#11) — deciding how to integrate critique_guidance into `_apply_budget_pruning` without changing its return type or breaking `synthesize_report`. Settled on a generic `elif name in components` handler that mutates the components dict in-place. Slightly side-channel-ish but avoids signature churn.

2. **What did I consider fixing differently, and why didn't I?** For #11, I considered adding a dedicated parameter and return value for critique_guidance in `_apply_budget_pruning` (like sources/business_context). But that would grow the function signature every time a new component needs budget awareness. The generic handler is more extensible — any component in the dict gets truncated if pruned.

3. **Least confident about going into the next batch or compound phase?** The generic `elif name in components` truncation handler in `_apply_budget_pruning` could silently truncate sources/business_context if they somehow fall through to it (they're handled by earlier if/elif branches, so this shouldn't happen). But the fallthrough path exists and has no test specifically verifying it doesn't fire for those two components.
