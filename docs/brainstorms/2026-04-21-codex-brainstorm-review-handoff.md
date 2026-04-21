# Codex Brainstorm Review Handoff

## Prompt for Codex

```
Read these files first for project context:
  - HANDOFF.md
  - CLAUDE.md
  - docs/research/2026-03-09-entropy-fixes-roadmap.md (existing C29-31 roadmap)

Then read the brainstorm and all 5 appendices:
  - docs/brainstorms/2026-04-21-ten-steps-ahead-brainstorm.md (main brief)
  - docs/brainstorms/appendices/appendix-a-competitive-landscape.md
  - docs/brainstorms/appendices/appendix-b-h2-cycle-specs.md
  - docs/brainstorms/appendices/appendix-c-context-profile-evolution.md
  - docs/brainstorms/appendices/appendix-d-swarm-architecture.md
  - docs/brainstorms/appendices/appendix-e-h2-prioritization.md

Also read these for current architecture understanding:
  - research_agent/modes.py (frozen dataclass config)
  - research_agent/context_result.py (ContextProfile dataclass)
  - research_agent/skeptic.py (adversarial verification — the pattern H2 extends)
  - research_agent/agent.py (orchestrator — the pipeline H2 modifies)

This is a strategic brainstorm for making this research agent "10 steps ahead"
of Google's Deep Research Max. It proposes three horizons:
  H1 (C29-31): Finish entropy roadmap — epistemic foundation
  H2 (C32-35): Counter-search, confidence scoring, research memory, adaptive planning
  H3 (C36-39): Streaming, visualization, multi-source fusion, multi-agent swarm

Review this brainstorm for:

1. **Strategic coherence** — Does the three-horizon structure make sense?
   Is the "epistemic rigor" moat thesis defensible, or is it wishful thinking?
   Does the "generalized engine, business-specific configuration" positioning
   hold up given the PFE context file and the stated business goals?

2. **Dependency chain validity** — The brainstorm claims C32-35 are "mostly
   independent" of each other (all depend on C29, not on each other). Appendix E
   has the dependency graph. Verify this by reading the actual code — are there
   hidden dependencies the analysis missed?

3. **H2 ordering challenge** — The final ordering is C32→C33→C34→C35
   (counter-search → confidence → memory → adaptive planning). The priority
   agent recommended C33→C35 as the "only ship 2" pick. Is the chosen ordering
   correct, or should memory come before counter-search for faster workflow impact?

4. **ContextProfile evolution risk** — Appendix C proposes growing ContextProfile
   from 4 to 10 fields. The "5-minute context test" and "one-screen rule" are
   proposed simplicity constraints. Are these sufficient? Is the file-path
   reference pattern (for knowledge_graph, source_config, swarm_roles) the
   right complexity boundary, or will it create a maze of references?

5. **Swarm architecture feasibility** — Appendix D proposes a 5-role swarm with
   blackboard pattern. The minimum viable swarm is 4 roles. Is the blackboard
   pattern (in-memory dict with phase boundaries) the right choice over message
   passing? Is distributing the skeptic across swarm roles (evidence→Verifier,
   timing→Temporal, frame→Contrarian) better than keeping it as a unified post-
   synthesis pass?

6. **What's missing?** — Are there capabilities, risks, or competitors the
   brainstorm doesn't address? The competitive landscape (Appendix A) covers
   Google, OpenAI, Perplexity, Exa, Tavily, and open-source agents. Is anyone
   or anything missing?

7. **Feed-Forward risks** — The brainstorm's three "least confident" items are:
   (a) Adaptive planning confidence at 65% — riskiest refactor in H2
   (b) ContextProfile growing from 4→10 fields without becoming unwieldy
   (c) Confidence extraction prompt — metacognitive task less studied than
       evidence-tier labeling
   Are these the right risks to flag, or are there bigger ones hiding?

Output: Findings ordered by severity (P1 blockers, P2 significant, P3 polish).
For each finding, state what's wrong and what should change.

Then provide a Claude Code handoff prompt that instructs Claude Code to:
1. Address findings that require brainstorm changes
2. Update the Feed-Forward section if risks shift
3. Confirm the brainstorm is ready for the Plan phase
```
