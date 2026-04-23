---
cycle: 31
date: 2026-04-23
modules: [decompose, modes, agent, mcp_server, results]
tags: [novelty-decomposition, MCP-tools, frozen-dataclass, prompt-engineering, agent-parity]
problem_type: feature-implementation
---

# Novelty-Biased Decomposition + MCP Critique History

## What Was Shipped

Two independent features in one PR on branch `feat/31-novelty-decomposition-mcp-critique`:

### 1. Novelty-Biased Decomposition

Added `novelty_queries: int` field to `ResearchMode` (quick=0, standard=1, deep=2). When > 0, appends `NOVELTY_INSTRUCTION_TEMPLATE` to the decompose system prompt asking the LLM to frame N sub-queries toward contrarian/underrepresented angles. Total sub-query count (2-3) is unchanged -- this reframes, not adds.

**Key design decisions:**
- **Reframe, not additive.** The prompt says "of the sub-queries you generate, frame N..." -- it doesn't ask for extra queries. This preserves the existing validation pipeline unchanged.
- **Module-level constant for prompt text.** `NOVELTY_INSTRUCTION_TEMPLATE` in `decompose.py` follows the C29 vocabulary pattern (`EVIDENCE_TIER_INSTRUCTION`, `ABSTENTION_INSTRUCTION`). Separates prompt content from control flow.
- **System prompt refactored to variable.** The inline string in `client.messages.create(system=...)` was extracted to a `system_prompt` variable for conditional append. This is the synthesize.py concatenation pattern applied to decompose.py.
- **Per-sub-query overlap requirement.** The novelty instruction explicitly says "each sub-query must retain at least one core term from the original query" to match `require_reference_overlap=True` in `validate_query_list()`. The existing prompt rule "keep key terms in at least one sub-query" was insufficient because validation applies per-query.

### 2. MCP `get_critique_history` Tool

Thin wrapper around `load_critique_history()` from context.py. Returns formatted text or user-friendly "no history" message. Uses `except Exception` boundary catch-all (MCP server boundary pattern from C19).

**Parity outcome:** After this PR, all functional CLI capabilities are agent-accessible. Three CLI-specific flags intentionally excluded: `--output`, `--open`, `--verbose`. The `--cost` tool was dropped during plan deepening (redundant with `list_research_modes`).

## Review Findings and Fixes

7-agent review found 0 P1, 4 P2, 2 P3. All resolved:

| Finding | Fix | Pattern |
|---------|-----|---------|
| Docstring missing `temperature` + `novelty_queries` (P2) | Added 2 lines to Args section | Keep docstrings in sync with signatures |
| No runtime type guard on `novelty_queries` (P2) | Added isinstance + range check at function boundary | Defense-in-depth: validate at boundary, not just caller |
| Magic number 3 coupled to `MAX_SUB_QUERIES` via comment (P2) | Added cross-module invariant test | Machine-enforce comment couplings with tests |
| `critique_report` MCP doesn't save critiques (P2, pre-existing) | Added `save_critique()` call | MCP tools must match CLI side effects, not just return values |
| Missing `ContextResult.empty()` test (P3) | Added test | Cover all enum states in boundary tools |
| No integration test for agent.py threading (P3) | Added assertion to existing test | Verify parameter threading end-to-end |

## Lessons

### 1. MCP Parity Means Side Effects Too, Not Just Return Values

The `critique_report` MCP tool returned the same data as the CLI but didn't call `save_critique()`. This made agent-initiated critiques invisible to `get_critique_history`. The parity lint catches missing tools and instructions, but doesn't check that tools have matching side effects. When wrapping CLI commands as MCP tools, audit both the return value AND the disk/state side effects.

**Where this applies:** Any future MCP tool that wraps a CLI command with file I/O side effects.

### 2. Comment-Enforced Coupling Needs Machine Enforcement

`modes.py` validated `novelty_queries` against hardcoded `3` with a comment "Must match decompose.MAX_SUB_QUERIES". Three review agents flagged this independently. A direct import would create a circular dependency, so the fix was a test that imports both and asserts the invariant. Comments document intent; tests enforce it.

**Where this applies:** Any cross-module constant that can't be shared via import due to circular deps.

### 3. Prompt Variable Extraction is the Prerequisite for Conditional Append

The system prompt in `decompose_query()` was an inline string argument. To conditionally append the novelty instruction, it had to be extracted to a variable first. This is a two-step refactor: (1) extract to variable (pure refactor, identical output), (2) add conditional append. Doing both in one step makes the diff harder to review.

**Where this applies:** Any prompt in the codebase that needs conditional extension -- extract first, modify second.

### 4. Frozen Dataclass Field Addition Is a 6-File Checklist

Adding `novelty_queries` to `ResearchMode` required changes in 6 locations: modes.py (field + validation + factory methods), results.py (ModeInfo), __init__.py (list_modes threading), mcp_server.py (list_research_modes output), agent.py (call site threading), and the plan already defers `to_mode_info()` to reduce this. This is the #1 recurring review finding (C19, 26, 27, 28, 30, 31).

**Checklist for future field additions:**
1. `modes.py` -- field with default + `__post_init__` validation + factory methods
2. `results.py` -- `ModeInfo` field with matching default
3. `__init__.py` -- `list_modes()` threading
4. `mcp_server.py` -- `list_research_modes()` output
5. `agent.py` -- call site(s) threading
6. Tests -- validation, threading, MCP output

## Deferred Items

- **A/B live validation of novelty decomposition** -- run when API keys renewed
- **Diversity gate threshold tuning** -- monitor SHORT_REPORT frequency after novelty is live
- **`META_DIR` promotion to public location** -- 3 consumers, accepted as existing pattern
- **`to_mode_info()` method on ResearchMode** -- eliminates manual 6-file sync

## Three Questions

1. **Hardest pattern to extract from the fixes?** The "MCP parity means side effects too" lesson. The critique_report gap was pre-existing (not introduced by C31), but became visible only because get_critique_history created the feedback loop. The pattern is: parity isn't just about return values -- audit file writes, state mutations, and cache updates too. This is hard to automate (the lint can't know what side effects should exist).

2. **What did you consider documenting but left out, and why?** The TOCTOU symlink gap in critique file loading (security-sentinel P2-1). It's pre-existing, requires local filesystem write access, and the strict YAML schema validation limits exploitation. Documenting it here would suggest it's related to C31 when it's actually a general infrastructure concern.

3. **What might future sessions miss that this solution doesn't cover?** The runtime interaction between novelty-framed sub-queries and the C30 diversity gate. The architectural safety nets are in place, but contrarian perspectives may systematically score lower on relevance, causing more SHORT_REPORT downgrades. This is only detectable with live queries -- no amount of code review catches it. The A/B validation script (`scripts/validate_cutoff_ab.py`) needs an API key renewal before it can run.
