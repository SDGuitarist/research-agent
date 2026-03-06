# Codex Repo Instructions

## Repo Snapshot
- Project: Python CLI research agent for Pacific Flow that searches the web and produces markdown reports with citations.
- Read first: `CLAUDE.md`, `HANDOFF.md`, `README.md`, then `docs/plans/`, `docs/solutions/`, and `todos/`.
- Main entry point: `main.py`
- Main package: `research_agent/`
- Tests: `tests/`
- Optional context files: `contexts/`
- Generated output: `reports/`
- Config: `pyproject.toml` (canonical dependency source)

## Environment
- `.env` must contain: `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`

## Commands
- Install for development and tests: `pip install -e ".[test]"` — installs the package plus test dependencies.
- Run a quick query: `python3 main.py --quick "your query"` — runs a fast research pass.
- Run the standard test suite: `python3 -m pytest tests/ -v` — runs the Python tests. Mock where the name is imported FROM, not where it's used.
- Run the MCP server: `research-agent-mcp` — starts the MCP server after the package is installed.

## Branch And PR Notes
- Base branch is `main`.
- Commit style: `type(scope): description` — e.g. `feat(search): add query validation`.
- If PR commands are needed, use `gh pr create --base main`.

## How Codex Should Work Here
- Use Codex for second-opinion planning, branch risk review, plain-English explanation, and focused Claude Code handoff prompts.
- Planning is analysis only unless I explicitly ask for implementation.
- When asked to plan, include prior phase risk, smallest safe slice, acceptance checks, rollback, and a handoff prompt.
- When asked to review, focus on search correctness, source handling, safety defenses, missing tests, and user-visible report regressions.

## Repo Guardrails
- Treat `reports/` as generated output unless I explicitly ask to edit a report.
- Preserve shared sanitization and safety patterns unless I explicitly ask for a redesign.
