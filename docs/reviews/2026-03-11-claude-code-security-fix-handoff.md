# Claude Code Security Fix Handoff

```text
Read docs/reviews/2026-03-11-codex-security-review.md. Fix the confirmed security issues only; do not do a broad refactor.

Scope:
- research_agent/summarize.py
- research_agent/synthesize.py
- research_agent/context.py
- research_agent/agent.py
- research_agent/mcp_server.py
- research_agent/report_store.py
- research_agent/safe_io.py
- research_agent/cascade.py
- tests/test_summarize.py
- tests/test_synthesize.py
- tests/test_context.py
- tests/test_mcp_server.py
- tests/test_safe_io.py
- tests/test_cascade.py

Job:
1. Sanitize untrusted URL strings before they enter prompt XML in summarize/synthesize.
2. Enforce symlink-safe containment for context discovery, preview, auto-detect selection, and loading. Do not preview or load context files that resolve outside the literal contexts/ root.
3. Enforce symlink-safe containment for reports/ and reports/meta/. get_report, auto-save, and critique-history loading must not follow base-dir symlinks outside the literal repo-local roots.
4. Prevent cascade fallback from forwarding URLs whose hostnames resolve to private/internal IPs to Jina Reader or Tavily Extract.
5. While touching auto-detect context, add a defensive system prompt and sanitize context names used in that prompt.

Acceptance criteria:
- Existing explicit path-traversal protections still pass.
- New regression tests cover malicious URL values in prompts.
- New regression tests cover symlinked contexts, symlinked reports roots, and symlinked critique-history files.
- New regression tests cover a hostname that resolves private even though it is not a literal private IP string.
- Preserve current CLI and MCP public interfaces unless a tiny compatibility-safe helper change is enough.
- Do not redesign MCP authentication, transport defaults, report format, or context UX beyond the required hardening.

Required checks:
- python3 -m pytest tests/test_summarize.py tests/test_synthesize.py tests/test_context.py tests/test_mcp_server.py tests/test_safe_io.py tests/test_cascade.py -v
- python3 -m pytest tests/ -q

Rollback and stop conditions:
- If the repo intentionally relies on symlinked reports/ or contexts/ roots, stop and document the exact workflow break before changing behavior.
- If cascade hardening requires a larger shared fetch API redesign, stop after proposing the smallest compatible helper extraction.
- End after code, tests, and a short summary of the security changes plus any residual risk.
```
