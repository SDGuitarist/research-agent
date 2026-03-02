---
title: Query Iteration — Auto-Refine + Predictive Follow-Up Questions
date: 2026-03-01
status: brainstorm
cycle: 20
tags: [query-iteration, refinement, follow-up, synthesis]
---

# Query Iteration — Auto-Refine + Predictive Follow-Up Questions

## What We're Building

The research agent currently decomposes a query into sub-queries and searches for exactly what the user asked. But users don't always ask the right question on the first try. This feature makes the agent iterate on the question itself:

1. **Auto-refine (during the run):** After the first research pass, the agent evaluates what it found, generates 1-2 refined versions of the question that would fill gaps or reframe the topic, and researches those too. One refinement pass — not a loop.

2. **Predictive follow-ups (at the end):** After generating the main report, the agent predicts 2-3 questions the user would likely ask next and pre-researches them. Results appear as appended sections after the main report.

## Why This Approach

Users prompt research engines with imperfect questions. The agent already decomposes queries (sub-queries explore different facets of the same question), but it never asks "what's a better version of this question?" or "what would the user want to know next?"

This is different from the existing gap-aware loop (Cycle 17), which tracks structured intelligence gaps across runs via YAML. This feature operates within a single run — no persistence needed.

**One refinement pass** keeps it predictable. The agent won't spiral into recursive self-improvement. Research → evaluate → refine → research again → report → follow-ups → done.

## Key Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Refinement depth | One pass, not a loop | Predictable cost and runtime. YAGNI — one pass catches the biggest gaps. |
| Follow-up behavior | Pre-research, not just suggest | The whole point is finding things the user wouldn't find alone. Suggestions alone don't add research value. |
| Output format | Appended sections after main report | Main report stays clean. Follow-ups are clearly separated as `## Follow-Up: [Question]` sections. |
| Mode support | Standard + deep only | Quick mode stays fast. Standard gets refinement + 2 follow-ups. Deep gets refinement + 3 follow-ups. |
| Pattern to follow | Skeptic pass (`skeptic.py`) | Same shape: post-analysis of draft, async execution, frozen dataclass output, graceful error isolation. |

## How It Fits the Pipeline

Current pipeline (standard mode):
```
decompose → search (pass 1) → refine_query → search (pass 2)
→ fetch/extract/summarize → relevance gate → coverage retry
→ draft → skeptic → synthesize_final → return report
```

With query iteration:
```
decompose → search (pass 1) → refine_query → search (pass 2)
→ fetch/extract/summarize → relevance gate → coverage retry
→ draft → skeptic → synthesize_final (main report complete)
→ [NEW] generate refined queries from draft gaps → research them → append as "Deeper Dive" sections
→ [NEW] predict follow-up questions → pre-research them → append as "Follow-Up" sections
→ return report
```

**Important:** Both the refined query results and follow-up results are *appended* sections — they do not modify the main report. The main report is already finalized by `synthesize_final()`. This keeps the architecture additive (no re-synthesis) and the insertion point clean: after `synthesize_final()` in `_evaluate_and_synthesize()`, before returning.

## Architecture Sketch

### New files
- `research_agent/iterate.py` — Query iteration logic (one file per stage, additive pattern)

### New frozen dataclasses
- `IterationResult(refined_queries: tuple[str, ...], rationale: str)` — Output of the refinement step
- `FollowUpResult(questions: tuple[str, ...], rationale: str)` — Output of the prediction step

### New mode parameters (in `modes.py`)
- `query_iterations: int` — 0 for quick, 1 for standard, 1 for deep
- `followup_questions: int` — 0 for quick, 2 for standard, 3 for deep
- `iteration_sources: int` — sources per refined/follow-up query (2-3)

### Integration points in `agent.py`
- After `synthesize_final()` in `_evaluate_and_synthesize()`
- Wrapped in try/except with graceful degradation (same as skeptic guard)
- Updates `_step_total` counter for progress display

### Synthesis for appended sections
- New `synthesize_iteration()` in `synthesize.py` — generates a mini-report per refined query ("Deeper Dive" sections)
- New `synthesize_followup()` in `synthesize.py` — generates a mini-report per follow-up question
- Concatenated to main report: `report + "\n\n" + iteration_sections + "\n\n" + followup_sections`
- Neither function modifies the main report — strictly additive

## Scope Boundaries

**In scope:**
- `iterate.py` with refinement + follow-up generation
- Mode parameter additions
- `agent.py` integration
- `synthesize.py` follow-up section generation
- Tests for all new code

**Out of scope:**
- Cross-run persistence (save findings for future runs) — separate feature
- User-configurable iteration count via CLI flags — modes handle this
- Changing the decompose step — iteration is a separate stage, not a replacement
- Modifying the gap-aware loop — different system entirely

## Open Questions

None — all key decisions resolved during brainstorming dialogue.

## Feed-Forward

- **Hardest decision:** Whether follow-ups should be suggestions-only or pre-researched. Pre-research adds real value but roughly doubles the API cost for standard mode. Chose pre-research because "finding things the user wouldn't find alone" is the core value proposition.
- **Rejected alternatives:** (1) Loop-until-satisfied refinement — too expensive and unpredictable. (2) Mode-dependent scaling (quick gets refinement, standard gets more, deep gets most) — added complexity for marginal benefit over the simpler "off for quick, on for standard/deep" split. (3) Separate files per follow-up — unnecessary file sprawl when appended sections work.
- **Least confident:** Whether the refinement step is meaningfully different from what decompose + coverage retry already do. Decompose splits into facets, coverage retry searches for more sources on weak sub-queries, and refinement would reframe the question itself. The plan phase must define a concrete prompt that produces queries *decompose would never generate* — otherwise this is wasted API calls. Test with 3-5 real queries to verify differentiation before committing to the architecture.
