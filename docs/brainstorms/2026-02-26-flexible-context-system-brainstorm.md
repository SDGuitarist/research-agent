# Brainstorm: Flexible Context System

**Date:** 2026-02-26
**Status:** Complete
**Risk from prior phase:** "unaudited prompts in decompose.py and relevance.py that may assume business context" — Audit found prompts are safe (all conditional), but hardcoded business-domain assumptions exist in context.py, synthesize.py, modes.py, and summarize.py.

## What We're Building

A flexible context system that lets the research agent work in three modes:

1. **Pacific Flow competitor analysis** — current behavior, business sections, competitor templates
2. **Pacific Flow general research** — uses PFE context for relevance but generic report structure
3. **General research** — no business context, fully generic reports

Currently the agent hardcodes Pacific Flow's specific document structure ("Two Brands, One Operator", "Key Differentiators", etc.) in `context.py` and business-specific report templates in `synthesize.py` and `modes.py`. This means:
- Changing `research_context.md`'s section layout breaks context slicing silently
- Non-competitor queries with business context still get competitor-analysis sections
- General research without any context works fine (conditional gates protect this path)

## Why This Approach

Three-layer design: flexible parsing (foundation) + multiple context files (explicit) + auto-detect (convenience).

### Layer 1: Flexible Section Detection (Foundation)

**What:** Replace hardcoded section names in `context.py` with a parser that reads whatever sections exist in any context file and categorizes them (search-relevant vs. synthesis-relevant) based on content, not names.

**Why:** This is the root cause. The hardcoded `_SEARCH_SECTIONS` and `_SYNTHESIS_SECTIONS` sets assume one specific document. Making parsing flexible means any context file "just works."

**Approach:** Instead of matching exact section headers, pass the full context file content through to the LLM. The current section-slicing optimization (only passing "search-relevant" or "synthesis-relevant" sections) saved tokens but introduced fragile coupling to specific headers. Passing the full file is simpler and lets the LLM decide what's relevant. If token cost becomes a problem, add section filtering later based on actual usage data.

### Layer 2: Multiple Context Files (Explicit Control)

**What:** A `--context` CLI flag that picks which context file to load.

**How it works:**
- `--context pfe` → loads `contexts/pfe.md` (current research_context.md, moved)
- `--context music` → loads `contexts/music.md` (future project)
- `--context none` → no context loaded, fully general mode
- No flag → falls back to Layer 3 (auto-detect) or default `research_context.md`

**File structure:**
```
contexts/
├── pfe.md          # Pacific Flow Entertainment (current file)
├── music.md        # Future: music project context
└── ...
```

### Layer 3: Auto-Detect from Query (Convenience)

**What:** When no `--context` flag is given, the agent examines the query and available context files to decide which (if any) to load.

**How it works:**
- List available context files in `contexts/`
- Read the first few lines (title/description) of each
- Ask the LLM: "Given this query, which context file (if any) is relevant?"
- Load the matched file, or none if no match

**Failure modes:**
- LLM picks wrong context file → wrong domain framing in report (user can override with `--context` next time)
- No context files exist → general mode, no harm
- LLM call fails → fall back to no context (general mode), log a warning

**Fallback:** If no `contexts/` directory exists but `research_context.md` does, load it (backward compatible).

## Key Decisions

1. **Flexible parsing over hardcoded sections** — The parser adapts to any document structure instead of requiring specific headers.

2. **Three layers with clear priority** — Explicit flag > auto-detect > default file. Each layer is independent and testable.

3. **Context files live in `contexts/` directory** — Separates context from code. Each file is a self-contained domain description.

4. **Report template adapts to context content** — Instead of "business = 8 sections, no business = 4 sections", the LLM generates domain-appropriate section structure based on the context file's content. A music industry context file would get music-relevant sections, not "Company Overview" and "Service Portfolio." This requires the synthesis step to read the context and produce a section outline before drafting. Adds complexity (extra LLM call, harder to test, less predictable output) but makes the tool genuinely domain-agnostic.

5. **Preserve current PFE behavior** — Moving `research_context.md` to `contexts/pfe.md` and passing `--context pfe` should produce similar output to today. See Open Questions for tension with Decision #4.

## What Changes (by file)

| File | Change | Why |
|------|--------|-----|
| `context.py` | Replace `_SEARCH_SECTIONS` / `_SYNTHESIS_SECTIONS` with flexible parser | Root cause of silent failure |
| `synthesize.py` | Template selection based on context content, not just boolean flag | Reports match the actual domain |
| `modes.py` | Remove hardcoded business section instructions from mode defaults | Mode config shouldn't assume domain |
| `summarize.py` | Make structured extraction generic (minor) | "Persuasion approach" hint is business-biased |
| `cli.py` / `main.py` | Add `--context` flag | User control over which context to load |
| `agent.py` | Wire new context loading through pipeline | Orchestrator passes context through |
| `decompose.py` | No change needed | Already conditional and generic |
| `relevance.py` | No change needed | Already context-free by design |

## Open Questions

1. **PFE backward compatibility vs. dynamic templates** — Decisions #4 and #5 conflict. If PFE context goes through dynamic template generation, the report sections may differ from today's hardcoded 8-section format. Options: (a) keep PFE's template hardcoded as a known-good default, only use dynamic for new context files; (b) let all contexts (including PFE) go through dynamic generation, accept output may change; (c) hybrid — use PFE's hardcoded template as the *seed example* that the LLM uses to generate templates for other domains. Plan phase must resolve this.

## Feed-Forward

- **Hardest decision:** Whether auto-detect (Layer 3) is worth the complexity. It adds an LLM call and can guess wrong. We included it because the user wants zero-friction general research without remembering flags.
- **Rejected alternatives:** (1) CLI mode flags (`--business`/`--general`) — mixes depth and context concerns, confusing. (2) Flexible sections only (no multiple files) — one context at a time, requires editing the file to switch.
- **Least confident:** Dynamic template generation (Key Decision #4). Having the LLM produce domain-appropriate report sections from the context file is powerful but hard to test and less predictable than hardcoded templates. Plan phase should define guardrails (e.g., minimum required sections, fallback to generic if LLM output is malformed).
