# Cycle 31 Brainstorm: Novelty-Biased Decomposition + MCP Tools #123

**Date:** 2026-04-22
**Cycle:** 31
**Theme:** Research Distinctiveness
**Prior phase:** Cycle 30 compound (complete)

## Prior Phase Risk

> "Whether diversity gate + relevance cutoff combined causes too many short_report downgrades for niche queries."

This is a live-data concern requiring API key renewal to validate. Noted as an interaction risk — novelty decomposition may actually help by broadening the source pool for niche topics, reducing diversity gate pressure.

## What We're Building

Two independent features shipping in one PR:

### Feature 1: Novelty-Biased Decomposition

Add a novelty instruction to the existing decomposition prompt so that some sub-queries target underrepresented or contrarian angles instead of centroid/obvious results.

- **Deep mode:** of the 2-3 sub-queries, 2 get novelty framing (total count unchanged)
- **Standard mode:** of the 2-3 sub-queries, 1 gets novelty framing (total count unchanged)
- **Quick mode:** unchanged (speed priority, usually SIMPLE classification anyway)

This addresses entropy audit finding #11: queries decompose into near-synonyms that return overlapping results, collapsing information diversity.

### Feature 2: MCP `--cost` + `--critique-history` Tools (#123)

Wrap the existing CLI `--cost` and `--critique-history` flags as MCP tools. Both already have working implementations in `cli.py` / `context.py` — this is a parity gap, not new functionality.

- Issue #123, deferral count 1 (promote-or-drop at 2 — shipping now)

## Why This Approach

### Novelty decomposition: prompt injection over templates or second LLM call

- **Simplest approach:** One prompt, one API call, no new code paths. The existing `decompose_query()` system prompt gets an additional instruction.
- **Epistemic calibration study evidence:** Prompts framing like "mechanisms most people overlook" reliably pushed the model past centroid explanations (study section 3.1). This is a validated prompting technique.
- **Configuration via ResearchMode:** A `novelty_queries: int` field on the frozen dataclass (0/1/2 per mode) controls how many of the existing sub-queries get novelty framing. Follows the pattern from temperature fields (C27). Testable, explicit, no mode-name coupling.

### MCP tools: thin wrappers matching existing pattern

- All 8 existing MCP tools return formatted strings, not structured data. Cost and critique-history tools follow the same pattern.
- No parameters for critique-history (matches CLI behavior). Cost tool takes no params either.
- `load_critique_history()` and `show_costs()` already exist — MCP tools are ~10-line wrappers each.

## Key Decisions

1. **Deep + standard get novelty; quick does not.** Quick mode optimizes for speed with 4 sources — novelty sub-queries would add noise without enough sources to benefit from diversity.

2. **Prompt injection, not template or second call.** Single prompt modification is simplest. Template approach is too rigid ("What aspects of [topic] are underrepresented...") — the LLM can generate better novelty angles with context. Second call doubles decomposition cost for marginal benefit.

3. **`novelty_queries: int` field on ResearchMode.** Follows the frozen dataclass pattern established by temperature fields. Values: quick=0, standard=1, deep=2. Decompose reads this field to decide how many of the existing sub-queries should get novelty framing. Total sub-query count (2-3) does not change.

4. **MCP tools return formatted text.** Matches `list_research_modes()` pattern. MCP clients render markdown nicely.

5. **No params on critique-history tool.** The CLI takes no params, `load_critique_history()` defaults are correct, and adding `limit` is YAGNI until someone asks for it.

6. **One PR for both features.** Both are small (~40 + ~80 lines), same cycle, independent but related by theme (research distinctiveness). MCP lint CI catches any parity gaps.

## Scope Boundaries

### In scope
- Modify decompose prompt to include novelty instruction when `novelty_queries > 0`
- Add `novelty_queries` field to `ResearchMode` with per-mode defaults
- Thread `novelty_queries` from mode into `decompose_query()`
- Add `show_costs()` and `get_critique_history()` MCP tools
- Tests for novelty decomposition (prompt content, field validation, mode threading)
- Tests for MCP tools (output format, error handling)
- MCP lint passes

### Out of scope
- A/B testing novelty decomposition effectiveness (needs live API key)
- Changing the number or structure of non-novelty sub-queries
- Adding new CLI flags
- Changing critique history aggregation logic
- Structured/JSON MCP responses

## Open Questions

None — all design decisions resolved during brainstorm dialogue.

## Feed-Forward

- **Hardest decision:** Whether to scope novelty to deep-only (roadmap) or include standard. Chose deep+standard because standard is the default mode and users benefit from diversity there too, but standard only gets 1 novelty sub-query to limit risk.
- **Rejected alternatives:** Template sub-queries (too rigid, can't use context), second LLM call (doubles cost), mode-name checks (breaks dataclass-as-config pattern), structured MCP data (breaks existing pattern).
- **Least confident:** Whether the novelty prompt instruction will produce meaningfully different sub-queries without being so vague that it degrades decomposition quality. The epistemic calibration study gives confidence, but the exact wording needs iteration during planning.

## Three Questions

1. **Hardest decision in this session?** Expanding novelty scope beyond the roadmap's deep-only to include standard mode. The roadmap was conservative, but standard is the default — if novelty decomposition works, most users should benefit.
2. **What did you reject, and why?** Template sub-queries — they're predictable but brittle. A hardcoded "What aspects of [topic] are underrepresented..." doesn't adapt to context or critique guidance the way prompt instructions do.
3. **Least confident about going into the next phase?** The exact prompt wording for the novelty instruction. "Mechanisms most people overlook" worked in the study, but decompose.py generates search queries, not explanations — the novelty framing needs to produce good search engine queries, not just interesting angles.
