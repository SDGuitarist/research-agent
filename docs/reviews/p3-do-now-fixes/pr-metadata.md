# PR Metadata: P3 "Do Now" Fixes

**Branch:** main (direct commits)
**Commits:** 8ecfdb3, e647405, 9dde2c4, 8420227
**Date:** 2026-02-23
**Plan:** docs/plans/2026-02-23-p3-do-now-fixes-plan.md

## Summary

5 small fixes from P3 triage, committed directly to main:

1. **#28** — Reject bool values in critique YAML validation (context.py)
2. **#29** — Skip critique history load in quick mode (agent.py)
3. **#25** — Extract `_scores` property to deduplicate tuple (critique.py)
4. **#26+#30** — Remove redundant sanitize calls (decompose.py, relevance.py)

## Files Changed

- research_agent/agent.py
- research_agent/context.py
- research_agent/critique.py
- research_agent/decompose.py
- research_agent/relevance.py
- tests/test_context.py
