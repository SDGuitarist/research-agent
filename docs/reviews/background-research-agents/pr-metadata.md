# PR Metadata — Background Research Agents

**Branch:** main
**Feature:** Background Research Agents (queue + digest skills, context system)
**Commit Range:** 52e32bf..aae39bb (23 commits)
**Date:** 2026-02-26

## Title

Background research agents: queue/digest skills + context system refactor

## Description

This feature adds two Claude Code skills (`/research-queue` and `/research-digest`) that enable background research processing. Key changes:

1. **Skills** (`.claude/skills/`): Queue skill parses `reports/queue.md`, launches background research agents with budget tracking. Digest skill reads completed reports via sub-agents for context protection.
2. **Context system** (`research_agent/context.py`): Refactored from hardcoded `research_context.md` to generic `contexts/` directory with `--context` CLI flag and auto-detect from query.
3. **Security**: Path traversal prevention in `resolve_context_path()`, query/preview sanitization in auto-detect prompt, XML tag boundary defense.
4. **API** (`research_agent/__init__.py`): Added `context` parameter to `run_research()` and exported context utilities.
5. **Synthesize** (`research_agent/synthesize.py`): Renamed XML tags, conditional templates based on context presence.

## Files Changed (Python + Skills)

- `.claude/skills/research-digest/SKILL.md` — new
- `.claude/skills/research-queue/SKILL.md` — new
- `contexts/pfe.md` — new (Pacific Flow Entertainment context)
- `research_agent/__init__.py` — export context utilities
- `research_agent/agent.py` — context parameter threading
- `research_agent/cli.py` — `--context` flag
- `research_agent/context.py` — major refactor (auto-detect, path validation)
- `research_agent/decompose.py` — XML tag rename
- `research_agent/modes.py` — XML tag rename
- `research_agent/synthesize.py` — conditional templates, XML tag rename
- `tests/test_agent.py` — auto-detect integration tests
- `tests/test_context.py` — path traversal, sanitization tests
- `tests/test_decompose.py` — XML tag rename
- `tests/test_public_api.py` — new (context parameter tests)
- `tests/test_synthesize.py` — template tests

## Focus Areas for Review

1. Skill file structure and logic (queue parsing, budget tracking, shell escaping)
2. Security: path traversal in `resolve_context_path()`, prompt injection defense in auto-detect
3. Context system architecture (ContextResult, auto-detect flow)
4. Budget tracking in queue skill (daily_spend.json)
5. Prior phase risk: digest skill discoverability
