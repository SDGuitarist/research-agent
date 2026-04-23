---
title: "feat: Novelty-biased decomposition + MCP critique-history tool"
type: feat
status: active
date: 2026-04-23
origin: docs/brainstorms/2026-04-22-cycle-31-novelty-decomposition-mcp-tools-brainstorm.md
feed_forward:
  risk: "Whether the novelty prompt instruction will produce meaningfully different sub-queries without being so vague that it degrades decomposition quality"
  verify_first: false  # implementation-first; live validation deferred until API key renewal
---

# feat: Novelty-biased decomposition + MCP critique-history tool

## Overview

Cycle 31 ships two independent features in one PR:

1. **Novelty-biased decomposition** — Modify the decompose prompt so that N of the existing 2-3 sub-queries target underrepresented/contrarian angles instead of centroid results. Controlled by a `novelty_queries: int` field on `ResearchMode` (quick=0, standard=1, deep=2).

2. **MCP `get_critique_history` tool** (#123) — Wrap the existing CLI `--critique-history` flag as an MCP tool. Thin wrapper returning formatted text, no parameters. Closes the remaining parity gap from #123 (deferral count 1; `--cost` already covered by `list_research_modes`).

**`show_costs` dropped** (deepening decision): `list_research_modes` already exposes `cost_estimate`, `max_sources`, and `word_target` per mode — the exact same data `show_costs` would return. Adding a redundant tool increases lint/parity maintenance for zero new information. CLI `--cost` remains for human convenience; MCP agents use `list_research_modes`.

(See brainstorm: `docs/brainstorms/2026-04-22-cycle-31-novelty-decomposition-mcp-tools-brainstorm.md`)

## Prior Phase Risk

> "The exact prompt wording for the novelty instruction. 'Mechanisms most people overlook' worked in the study, but decompose.py generates search queries, not explanations — the novelty framing needs to produce good search engine queries, not just interesting angles."

This plan addresses it by: drafting a concrete prompt instruction that frames novelty in search-query terms ("angles that typical searches would miss"), not explanation terms ("mechanisms most people overlook"), and validating via three example trace-throughs across query types against `_validate_sub_queries()`. `verify_first` is set to `false` — this is implementation-first with offline fixture validation. Live A/B testing is deferred until API key renewal.

### C30 Feed-Forward Risk (Cross-Cycle)

> "Whether diversity gate + relevance cutoff combined causes too many short_report downgrades for niche queries. Standard mode requires 3 unique domains among 4+ surviving sources — for niche queries with few authoritative sites, this may be too strict."

Novelty decomposition explicitly targets niche/contrarian angles — exactly the scenario C30 flagged. This is an accepted interaction risk (see Technical Considerations and Risk 2 for full analysis).

## Problem Statement / Motivation

**Novelty decomposition:** Entropy audit finding #11 — queries decompose into near-synonyms that return overlapping results, collapsing information diversity. The epistemic calibration study (section 3.1) showed that novelty-framed prompts reliably push past centroid explanations. Adapting this for search queries should broaden the source pool.

**MCP tool:** Issue #123 at deferral count 1 (promote-or-drop at 2). CLI `--critique-history` has no MCP equivalent, breaking agent parity. (`--cost` covered by `list_research_modes` — see Overview.)

## Proposed Solution

### Feature 1: Novelty-Biased Decomposition

**What changes:**
- Add `novelty_queries: int` field to `ResearchMode` (quick=0, standard=1, deep=2)
- Add `novelty_queries: int = 0` parameter to `decompose_query()`
- When `novelty_queries > 0`, append a novelty instruction to the system prompt's Rules section
- Thread from `agent.py` via `self.mode.novelty_queries`
- Add `novelty_queries` to `ModeInfo` and `list_research_modes()` output

**What does NOT change:**
- Total sub-query count stays at 2-3 (reframe, not additive)
- SIMPLE classification behavior unchanged — novelty instruction is in the prompt but has no effect when LLM returns no sub-queries
- Validation rules in `_validate_sub_queries()` unchanged — novelty sub-queries must pass the same overlap/word-count checks
- Quick mode unchanged (`decompose=False` means decomposition is skipped entirely)
- Downstream pipeline code (search, fetch, summarize, synthesize) untouched — though the *data* flowing through the diversity gate may change (see Technical Considerations)

**Prompt wording (draft):**

Define as a module-level constant in `decompose.py` (follows the vocabulary module pattern from C29 evidence tiers):

```python
NOVELTY_INSTRUCTION_TEMPLATE = (
    "- Of the sub-queries you generate, frame {novelty_queries} to target angles "
    "that typical searches would miss: lesser-known data, contrarian perspectives, "
    "or underrepresented aspects of the topic. Each sub-query — including novelty "
    "ones — must retain at least one core term from the original query so it "
    "stays grounded. These must still be effective search engine queries with "
    "specific, searchable terms."
)
```

**Appending strategy:** Build the system prompt string in a variable, then conditionally append the novelty instruction **after the last rule bullet** (after "Keep the original query's key terms in at least one sub-query"). This matches the `synthesize.py` concatenation pattern where `EVIDENCE_TIER_INSTRUCTION` and `ABSTENTION_INSTRUCTION` are appended to `mode_instructions`. Never splice mid-string.

```python
system_prompt = "You are a search query analyst..."  # existing string
if novelty_queries > 0:
    system_prompt += f"\n{NOVELTY_INSTRUCTION_TEMPLATE.format(novelty_queries=novelty_queries)}"
    # Safe: novelty_queries is a validated int from ResearchMode.__post_init__
```

**Why this wording works with validation — per-query overlap requirement:**

`_validate_sub_queries()` calls `validate_query_list()` with `require_reference_overlap=True`. This applies to **each sub-query individually** (`query_validation.py:122`): any sub-query sharing zero meaningful words with the original is rejected. The existing prompt rule "Keep the original query's key terms in at least one sub-query" is insufficient — it allows novelty sub-queries to share zero words. The novelty instruction explicitly adds "Each sub-query — including novelty ones — must retain at least one core term from the original query" to match the per-query validation contract.

The "effective search engine queries with specific, searchable terms" constraint prevents vague framings that would fail the 2-10 word count or produce poor search results.

**Example trace-throughs (3 query types):**

*Technical:*
- Original: "impact of AI on software development jobs"
- Meaningful words: {impact, ai, software, development, jobs}
- Normal sub-query: "AI automation software developer employment statistics 2026" — shares {ai, software} (passes overlap), 7 words (passes word count)
- Novelty sub-query: "software developer skills AI cannot replicate evidence" — shares {software, ai} (passes overlap), 8 words (passes word count), contrarian angle

*Market research:*
- Original: "luxury wedding music market San Diego"
- Meaningful words: {luxury, wedding, music, market, san, diego}
- Normal sub-query: "wedding music vendor pricing San Diego county" — shares {wedding, music, san, diego} (passes overlap), 7 words
- Novelty sub-query: "independent wedding musicians market share challenges" — shares {wedding, market} (passes overlap; "musicians" ≠ "music" — no hyphen split), 6 words, underrepresented angle

*Current events:*
- Original: "electric vehicle battery recycling regulations 2026"
- Meaningful words: {electric, vehicle, battery, recycling, regulations, 2026}
- Normal sub-query: "EV battery recycling policy compliance requirements" — shares {battery, recycling} (passes overlap), 6 words
- Novelty sub-query: "battery recycling informal sector environmental impact" — shares {battery, recycling} (passes overlap), 6 words, lesser-known data angle

**Validation exit criteria:** A novelty sub-query passes `_validate_sub_queries()` when it has (1) at least 1 meaningful word shared with the original query, (2) between 2-10 words total, (3) < 80% overlap with the original (not a restatement), and (4) no near-duplicate with other sub-queries at 70% threshold.

### Feature 2: MCP `get_critique_history` Tool

**`get_critique_history` tool:**
- No parameters
- Imports `load_critique_history` from `research_agent.context` and `META_DIR` from `research_agent.agent` (private constant; accepted debt — `META_DIR` is not exported from `research_agent.__init__`, same pattern as `cli.py:15`)
- Returns `result.content` if available
- If fewer than 3 valid passing critiques: returns user-friendly message explaining the `overall_pass: true` threshold
- Includes `except Exception` boundary catch-all (required for any tool doing file I/O — matches `run_research` and `critique_report` pattern)

**Instructions string:** Add one sentence mentioning `get_critique_history` by name. Position it outside the workflow guidance ("Use get_critique_history to review patterns across past research runs"). MCP lint + test `test_all_tools_mentioned_in_instructions` enforce word-boundary matching.

**MCP controllability (intentional decision):** `novelty_queries` is observable via `list_research_modes` but NOT overridable from MCP clients. This is intentional — the CLI also can't override it (it's mode-locked). Agents pick a mode, the mode determines novelty behavior. Documented in `list_research_modes` output with a brief description: "novelty_queries: N sub-queries reframed for contrarian/underrepresented angles."

**Parity note:** After this PR, all *functional* CLI capabilities are agent-accessible. Three CLI-specific flags are intentionally excluded from MCP: `--output` (filesystem path), `--open` (macOS-only), `--verbose` (uses `MCP_LOG_LEVEL` env var instead).

## Technical Considerations

**Validation compatibility:** `validate_query_list()` applies `require_reference_overlap=True` to **each sub-query individually** (`query_validation.py:122`). Any sub-query sharing zero meaningful words with the original is rejected. The existing prompt rule "Keep the original query's key terms in at least one sub-query" does not satisfy this — it allows novelty sub-queries to share zero words. The novelty instruction template explicitly adds "Each sub-query — including novelty ones — must retain at least one core term from the original query" to match the per-query validation contract. Three trace-throughs across query types (technical, market research, current events) verify this works in practice.

**`novelty_queries` > actual sub-queries:** If deep mode asks for 2 novelty sub-queries but the LLM only generates 2 total, all 2 are novelty-framed. This is acceptable — it's a best-effort instruction, not a hard contract. No post-hoc enforcement.

**SIMPLE query interaction:** When `novelty_queries=1` and the LLM classifies as SIMPLE, the novelty instruction is present but has no effect on output. The instruction uses "Of the sub-queries you generate" — if no sub-queries are generated, it's a no-op. No risk of pressuring SIMPLE→COMPLEX misclassification.

**Diversity gate interaction (C30 cross-concern):** Novelty sub-queries target niche/contrarian angles, which may return sources from fewer authoritative domains. Combined with the C28 relevance cutoff (4 for standard/deep) and snippet score cap (3, below cutoff), niche novelty results that are snippet-only will be dropped, reducing both source count and domain count. This could increase `SHORT_REPORT` downgrade frequency for exactly the queries novelty is designed to help. The plan says "downstream pipeline untouched" — this is true structurally (no code changes downstream) but the *data flowing through* the diversity gate changes. This is an accepted interaction risk to monitor during live A/B testing.

**Noun-phrase fallback interaction:** If novelty sub-queries have low snippet quality, the noun-phrase fallback in `search.py` (C29) will extract their noun phrases for query refinement. Unusual novelty phrasing may produce weaker noun phrases. Acceptable risk — monitor in live testing.

## System-Wide Impact

- **Interaction graph:** `novelty_queries` flows: `ResearchMode` → `agent.py` → `decompose_query()` → system prompt. No callbacks, no observers. MCP tools are leaf functions with no side effects.
- **Error propagation:** If novelty sub-queries all fail validation, existing fallback returns original query. No new error paths.
- **State lifecycle risks:** None — all changes are stateless prompt modifications or read-only data tools.
- **API surface parity:** After this PR, all functional CLI capabilities are agent-accessible. Three CLI-specific flags are intentionally excluded (`--output`, `--open`, `--verbose`). `novelty_queries` is exposed in `ModeInfo` and `list_research_modes` for observability (mode-locked, not overridable). `--cost` covered by `list_research_modes`.

## Acceptance Tests

### Happy Path

- WHEN `novelty_queries=1` and query is COMPLEX THE SYSTEM SHALL include the novelty instruction in the decompose system prompt
- WHEN `novelty_queries=0` and query is COMPLEX THE SYSTEM SHALL NOT include the novelty instruction in the decompose system prompt
- WHEN `novelty_queries=2` and the LLM returns 3 sub-queries THE SYSTEM SHALL pass all 3 through existing validation unchanged
- WHEN `get_critique_history` MCP tool is called and `load_critique_history` finds 3+ valid passing critiques (`overall_pass: true`) THE SYSTEM SHALL return the summarized pattern text

### Error Cases

- WHEN `novelty_queries=-1` is passed to `ResearchMode()` THE SYSTEM SHALL raise `ValueError` in `__post_init__`
- WHEN `novelty_queries=4` is passed to `ResearchMode()` THE SYSTEM SHALL raise `ValueError` in `__post_init__` (exceeds MAX_SUB_QUERIES)
- WHEN `get_critique_history` is called with fewer than 3 valid passing critiques THE SYSTEM SHALL return a user-friendly "no history" message explaining the passing threshold, not an error
- WHEN `get_critique_history` encounters an unexpected exception THE SYSTEM SHALL return a sanitized `ToolError`, not a raw traceback
- WHEN `novelty_queries=1` and query is SIMPLE THE SYSTEM SHALL return the original query unchanged (novelty instruction has no effect)

### Security

- WHEN `novelty_queries=1` and `context_content` contains malicious instructions THE SYSTEM SHALL still produce valid sub-queries that pass `_validate_sub_queries()` (existing three-layer defense covers this; add one regression test)

### Invariants

- WHEN any mode runs with novelty enabled THE SYSTEM SHALL NOT change the total sub-query count (still 2-3)
- WHEN quick mode runs THE SYSTEM SHALL skip decomposition entirely (`decompose=False`)
- WHEN MCP lint runs THE SYSTEM SHALL pass with 0 missing tools
- C30 gate thresholds (`min_unique_domains`, `relevance_cutoff`, `min_sources_full_report`) SHALL NOT be modified in this cycle — interaction with novelty decomposition must be evaluated with live testing first (non-goal for C31)

### Test Mock Guidance

Mock novelty sub-queries in tests should be genuinely divergent from the original query (different angle, not synonym rearrangements), or the test passes without validating the interesting case. Example: for original "luxury wedding market trends", a good mock novelty response is "independent wedding vendor market share" (different angle), not "luxury market wedding analysis" (just rearranged words).

### Verification Commands

```bash
python3 -m pytest tests/ -v                    # all tests pass
python3 scripts/lint_mcp_parity.py             # 0 missing tools
python3 -m pytest tests/test_decompose.py -v   # novelty prompt tests
python3 -m pytest tests/test_mcp_server.py -v  # new tool tests
python3 -m pytest tests/test_modes.py -v       # field validation tests
```

## Implementation Sessions

### Session 1: Novelty decomposition — field + prompt + threading (~80 lines)

**Files:** `modes.py`, `results.py`, `__init__.py`, `decompose.py`, `agent.py`, `mcp_server.py`, `tests/test_modes.py`, `tests/test_decompose.py`, `tests/test_mcp_server.py`

**ResearchMode field:**
1. Add `novelty_queries: int = 0` field to `ResearchMode` in `modes.py:40` (after `synthesis_temperature`)
2. Set values in factory methods: `quick()` → 0, `standard()` → 1, `deep()` → 2
3. Add `__post_init__` validation: `0 <= novelty_queries <= 3` with comment `# Must match decompose.MAX_SUB_QUERIES`

**ModeInfo + MCP observability:**
4. Add `novelty_queries: int = 0` field to `ModeInfo` in `results.py:55`
5. Thread `novelty_queries=m.novelty_queries` in `list_modes()` in `__init__.py:182`
6. Add `novelty_queries` to `list_research_modes()` output in `mcp_server.py:301` with description: "novelty={m.novelty_queries}" (or similar brief label)

**Decompose prompt:**
7. Add `NOVELTY_INSTRUCTION_TEMPLATE` module-level constant in `decompose.py`
8. Add `novelty_queries: int = 0` parameter to `decompose_query()` signature in `decompose.py:67`
9. Build system prompt as variable, conditionally append novelty instruction after last rule bullet when `novelty_queries > 0`
10. Thread `novelty_queries=self.mode.novelty_queries` in `agent.py:476`

**Tests:**
11. Field present on all modes with correct values, validation rejects -1 and 4, ModeInfo populated
12. Verify prompt includes `NOVELTY_INSTRUCTION_TEMPLATE` when `novelty_queries=1`
13. Verify prompt excludes novelty instruction when `novelty_queries=0`
14. Verify SIMPLE classification still works with novelty instruction present
15. Verify genuinely divergent novelty sub-queries pass `_validate_sub_queries()` with mock response (see Test Mock Guidance above)
16. In `tests/test_mcp_server.py`: verify `novelty_queries` appears in `list_research_modes` output (MCP observability — lint checks tool names in instructions, but does not verify field visibility in output)

### Session 2: MCP `get_critique_history` tool + lint (~40 lines)

**Files:** `mcp_server.py`, `tests/test_mcp_server.py`

1. Add `get_critique_history()` tool with boundary catch-all:
   ```python
   @mcp.tool
   def get_critique_history() -> str:
       """Show summarized self-critique patterns from recent research runs.

       Returns aggregate quality patterns from recent research critiques,
       including weakest dimensions and recurring weaknesses. Requires at
       least 3 passing critiques (overall_pass: true) — failed critiques
       do not count toward this threshold.
       """
       from fastmcp.exceptions import ToolError
       from research_agent.context import load_critique_history
       from research_agent.agent import META_DIR  # accepted private import (see plan §4)

       try:
           result = load_critique_history(META_DIR)
       except Exception:
           logger.exception("Unexpected error in get_critique_history")
           raise ToolError(
               "Failed to load critique history. Check that the research-agent "
               "project root is accessible."
           )
       if result.content:
           return result.content
       return ("No critique history available. Need at least 3 passing "
               "critiques (overall_pass: true) to generate patterns. Run "
               "research in standard or deep mode with critique enabled.")
   ```
2. Update `mcp.instructions` string to mention `get_critique_history`: "Use get_critique_history to review patterns across past research runs."
3. Tests: output format with mocked passing history, no-history message (verify "passing" wording), 3 failing critiques → still no-history (threshold is passing critiques), exception → ToolError, tool in instructions
4. Run `python3 scripts/lint_mcp_parity.py` — 0 missing

## Dependencies & Risks

**Risk 1 (medium): Novelty instruction produces vague sub-queries.** Mitigation: prompt wording explicitly requires "effective search engine queries with specific, searchable terms." Existing validation catches vague/short queries. A/B testing with live API key (deferred) will validate effectiveness.

**Risk 2 (medium): Novelty sub-queries increase SHORT_REPORT downgrades via diversity gate.** Niche/contrarian novelty results may cluster on fewer domains and be snippet-tier (capped at score 3, below standard/deep cutoff 4). This reduces surviving source count and domain count. Mitigation: diversity gate is a post-decision downgrade (FULL→SHORT only, not failure). Monitor frequency during live testing. If too aggressive, `min_unique_domains` can be tuned per-mode in a future cycle.

**Risk 3 (low): Novelty sub-queries fail validation systematically.** Mitigation: novelty instruction explicitly requires "retain at least one core term from the original query" (matches per-query `require_reference_overlap` contract). Three trace-throughs across query types verify compliance. If this becomes an issue, `require_reference_overlap` can be relaxed for novelty queries in a future cycle.

**Risk 4 (low): Noun-phrase fallback produces weaker refinements for novelty sub-queries.** Novelty sub-queries with unusual phrasing may produce poorer noun phrases in the C29 refinement fallback path. Acceptable risk — monitor in live testing.

## Sources & References

- **Origin brainstorm:** [docs/brainstorms/2026-04-22-cycle-31-novelty-decomposition-mcp-tools-brainstorm.md](docs/brainstorms/2026-04-22-cycle-31-novelty-decomposition-mcp-tools-brainstorm.md) — Key decisions: reframe not additive, prompt injection approach, `novelty_queries: int` field, formatted text MCP output, one PR. Deepening dropped `show_costs` as redundant with `list_research_modes`.
- **C30 solution doc:** `docs/solutions/feature-implementation/summarization-context-preservation-diversity-truncation-abstention.md` — diversity gate interaction risk
- **Entropy roadmap C31:** `docs/research/2026-03-09-entropy-fixes-roadmap.md` lines 136-163
- **Epistemic calibration study:** section 3.1 (novelty framing), section 3.2 (temperature vs prompts)
- **MCP parity lint solution:** `docs/solutions/workflow/mcp-parity-lint-ci-enforcement.md`
- **Temperature threading precedent (C27):** `docs/solutions/feature-implementation/input-validation-and-generation-controls.md`
- **MCP boundary protection:** `docs/solutions/security/mcp-server-boundary-protection-and-agent-parity.md` — boundary catch-all pattern
- **C29 evidence tier vocabulary pattern:** `docs/solutions/feature-implementation/skeptic-enforcement-quality-gates-evidence-tiers.md` — module-level constant for prompt instructions
- **C20 conditional prompt templates:** `docs/solutions/logic-errors/conditional-prompt-templates-by-context.md` — appending strategy
- Related issue: #123

## Enhancement Summary

**Deepened on:** 2026-04-23
**Review agents used:** 9 (agent-native, architecture-strategist, pattern-recognition, code-simplicity, kieran-python, security-sentinel, C30-learnings, prompt-patterns, MCP-boundary)

### Key Improvements from Deepening
1. **Dropped `show_costs`** — redundant with `list_research_modes` (3 agents flagged independently)
2. **Added `except Exception` boundary** to `get_critique_history` (MCP boundary pattern)
3. **Added C30 diversity gate interaction risk** — novelty sub-queries affect downstream gate outcomes
4. **Defined `NOVELTY_INSTRUCTION_TEMPLATE` as constant** — follows C29 vocabulary module pattern
5. **Explicit prompt appending strategy** — after last rule bullet, matching `synthesize.py` concatenation
6. **Merged Sessions 1+2** — field + prompt are one coherent feature (2 sessions, not 3)
7. **Added MCP controllability decision** — mode-locked (intentional), with agent-facing description
8. **Added parity caveat** — three CLI-specific flags documented as intentionally excluded
9. **Security regression test** — verify malicious `context_content` doesn't steer novelty sub-queries

## Feed-Forward

- **Hardest decision:** Correcting the per-query validation assumption after Codex review. The original plan assumed the existing prompt rule "keep key terms in at least one sub-query" satisfied `require_reference_overlap=True` — it does not, because validation applies to each sub-query individually. The novelty instruction template now explicitly requires "retain at least one core term" per sub-query.
- **Rejected alternatives:** Boolean `novelty_bias` (simplicity reviewer argued false precision) — kept int because "frame 2" vs "frame 1" is a real signal even if best-effort. MCP override param for `novelty_queries` — rejected because CLI also can't override it, so adding MCP-only control creates asymmetric parity. `verify_first: true` — changed to `false` because live API testing is blocked by expired key; fixture-level validation in tests is sufficient for implementation.
- **Least confident:** Two independent unknowns: (1) whether the novelty prompt wording generalizes across diverse query domains (3 trace-throughs help but are not exhaustive), and (2) whether the diversity gate interaction (C30) degrades SHORT_REPORT frequency for niche queries. Both require live A/B testing after API key renewal. C30 thresholds are explicitly frozen in this cycle.

## Three Questions

1. **Hardest decision in this session?** Fixing the per-query validation contract. The original plan had an incorrect assumption about `require_reference_overlap` that would have caused novelty sub-queries to silently fail validation. The Codex review caught this — the prompt template now has an explicit per-sub-query overlap requirement.
2. **What did you reject, and why?** `verify_first: true` — the plan originally set this but had no real verification gate behind it. Changed to `false` with explicit acknowledgment that this is implementation-first. Live validation is deferred, not forgotten.
3. **Least confident about going into the next phase?** Whether 3 trace-throughs are sufficient to prove the prompt wording works across diverse query types. The fixture matrix covers technical, market research, and current events — but niche domains (medical, legal, highly specific industries) may produce sub-queries with unusual vocabulary that interacts differently with `meaningful_words()` stop-word filtering. Monitor in live testing.
