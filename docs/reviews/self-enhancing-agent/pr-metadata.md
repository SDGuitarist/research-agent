# PR Metadata — Self-Enhancing Agent

**Branch:** main (direct commits)
**Commit Range:** bad292e..57bf44e (4 commits)
**Date:** 2026-02-23

## Commits

1. `bad292e` feat(critique): add self-critique module with YAML output
2. `5b92ae4` feat(agent): wire self-critique into pipeline after synthesis
3. `edc45f0` feat(context): add load_critique_history for adaptive prompts
4. `57bf44e` feat(agent): thread critique history through pipeline stages

## Files Changed (12 files, +1091 -25)

- research_agent/agent.py — Orchestrator: added critique wiring + history threading
- research_agent/context.py — New: load_critique_history for adaptive prompts
- research_agent/critique.py — New: self-critique module with YAML output
- research_agent/decompose.py — Accept critique_context parameter
- research_agent/errors.py — New CritiqueError exception
- research_agent/relevance.py — Accept critique_context parameter
- research_agent/synthesize.py — Accept critique_context parameter
- tests/test_context.py — Tests for load_critique_history
- tests/test_critique.py — Tests for critique module
- tests/test_decompose.py — Tests for critique_context in decompose
- tests/test_relevance.py — Tests for critique_context in relevance
- tests/test_synthesize.py — Tests for critique_context in synthesize

## Summary

Adds a self-critique feedback loop to the research agent pipeline. After synthesis, the agent evaluates its own report for gaps, bias, and quality issues, producing YAML-structured critique results. Critique history is loaded from past reports and threaded through decomposition, relevance evaluation, and synthesis stages so the agent can learn from previous mistakes.
