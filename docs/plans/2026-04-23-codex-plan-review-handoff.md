# Codex Plan Review Handoff — Cycle 31

## Instructions

Read these files first for project context:
  - HANDOFF.md
  - CLAUDE.md
  - docs/plans/2026-04-23-feat-novelty-decomposition-mcp-cost-critique-plan.md

Review this plan for:
1. **Gaps** — anything missing that will cause problems during implementation
2. **Wrong assumptions** — does the plan assume something that isn't true?
3. **Scope creep** — anything in the plan that wasn't in the brainstorm
4. **The Feed-Forward "least confident" item** — is it addressed or still a risk?
5. **Plan Quality Gate** — does it answer: what's changing, what must not change, how we'll know it worked, most likely way it's wrong?

## Key Files to Check

- `research_agent/modes.py` — `ResearchMode` frozen dataclass (adding `novelty_queries: int` field)
- `research_agent/decompose.py` — query decomposition system prompt (adding novelty instruction)
- `research_agent/agent.py` — orchestrator call site for `decompose_query()` (threading `novelty_queries`)
- `research_agent/mcp_server.py` — MCP tools + instructions string (adding `get_critique_history`)
- `research_agent/results.py` — `ModeInfo` dataclass (adding `novelty_queries` field)
- `research_agent/__init__.py` — `list_modes()` function (threading new field)
- `research_agent/context.py` — `load_critique_history()` (wrapped by new MCP tool)
- `research_agent/cli.py` — existing `--cost` and `--critique-history` implementations

## Brainstorm Doc

`docs/brainstorms/2026-04-22-cycle-31-novelty-decomposition-mcp-tools-brainstorm.md`

Note: The plan dropped `show_costs` MCP tool during deepening (3/9 review agents flagged redundancy with `list_research_modes`). The brainstorm included it — verify this was the right call.

## Specific Review Guidance

### What Changed Between Brainstorm and Plan
- `show_costs` MCP tool removed (redundant with `list_research_modes`)
- `NOVELTY_INSTRUCTION_TEMPLATE` defined as module-level constant (C29 vocabulary pattern)
- `get_critique_history` gained `except Exception` boundary catch-all (MCP boundary pattern)
- Sessions merged from 3 to 2 (field + prompt are one feature)
- C30 diversity gate interaction risk documented (not in brainstorm)
- MCP controllability documented as intentionally mode-locked

### Feed-Forward Risk (Most Important)
> "The diversity gate interaction. Novelty sub-queries target exactly the niche/contrarian angles that C30 flagged as risky for `min_unique_domains`. This is an accepted risk, but the only real validation is live A/B testing after API key renewal."

Is this risk adequately mitigated, or should the plan include a fallback (e.g., reducing `min_unique_domains` when `novelty_queries > 0`)?

### Areas of Concern
1. **Prompt wording** — The novelty instruction says "frame {novelty_queries} to target angles that typical searches would miss." Will this produce genuinely different search queries, or just synonym rearrangements? The plan has one example trace-through — is that sufficient?
2. **Validation compatibility** — The plan claims novelty sub-queries will pass `require_reference_overlap=True` because the existing prompt says "keep original query's key terms." Is this assumption robust across diverse query types?
3. **`META_DIR` import** — The plan imports `META_DIR` from `agent.py` (a private constant in a 1000+ line file). Three review agents flagged this but accepted it as an existing pattern. Should this be promoted to a public location?

## Output

Findings ordered by severity (P1/P2/P3) + an updated Claude Code handoff prompt if the plan needs changes before implementation.
