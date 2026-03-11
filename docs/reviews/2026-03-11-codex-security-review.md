# Codex Security Review

Date: 2026-03-11
Repo: `research-agent`
Reviewer: Codex

## Executive Summary

No critical remote-code-execution, direct path-traversal, or confirmed SSRF bypass was found in the current tree. The core protections are real: fetch-time SSRF validation, redirect-by-redirect checks, loopback-only HTTP binding in the console MCP entrypoint, report filename validation, and context-name traversal checks.

The highest-signal issues are in prompt-input hardening and symlink-sensitive local containment. Three medium-severity issues and one low-severity hardening issue should be fixed next:

1. Untrusted URL strings are inserted into LLM prompts without sanitization.
2. Symlinked context files can bypass the intended `contexts/` containment model.
3. Symlinked `reports/` and `reports/meta/` roots can bypass the intended repo-local containment model.
4. Cascade fallback may disclose internal hostnames to third-party services because it does not DNS-resolve hostnames before forwarding failed URLs.

Severity is calibrated for the default deployment model in this repo: a trusted local operator running a single-user CLI. Findings that require local filesystem control are lower-severity here than they would be in a shared or hosted environment.

## Scope And Verification

- Read and reviewed the code paths for fetch/SSRF, prompt construction, MCP boundaries, report storage, context loading, and critique-history loading.
- Ran the full test suite: `python3 -m pytest tests/ -q`
- Result: `938 passed in 131.77s` on 2026-03-11.
- Reproduced the symlink-related issues in a temp workspace to confirm they are current behavior, not hypothetical.

## Medium Severity

### RA-SEC-001: Untrusted URL strings enter prompt XML without sanitization

Impact: a malicious or malformed URL from search/fetch results can break prompt boundaries or introduce instruction-like text into summarization and synthesis prompts.

Evidence:

- `summarize_chunk()` sanitizes `chunk` and `title`, but inserts raw `url` into `<webpage_metadata>` in `research_agent/summarize.py:87-115`.
- `_build_sources_context()` sanitizes titles and summaries, but inserts raw `url` into `<url>` in `research_agent/synthesize.py:753-756`.
- The current tests assert title/body sanitization, but not URL sanitization in `tests/test_summarize.py:178-200` and `tests/test_synthesize.py:72-87`.

Why this matters:

- Search-result URLs are external input.
- In `summarize.py`, the system prompt explicitly scopes the ignore-instructions rule to `<webpage_content>`, while the unsanitized URL sits in `<webpage_metadata>`.
- This is a prompt-integrity issue, not a classic filesystem or network exploit, but it is still worth fixing because the repo already relies on XML-style prompt fencing as a core defense.

Recommended fix:

- Sanitize all untrusted URL strings before inserting them into prompt XML.
- Add regression tests for malicious URL values containing XML-like delimiters.

### RA-SEC-002: Symlinked context files bypass the intended `contexts/` containment model

Impact: a symlink placed under `contexts/` can expose arbitrary local file contents through context previews, auto-detection input, and full context loading.

Evidence:

- `resolve_context_path()` blocks separator-based traversal for explicit names in `research_agent/context.py:229-244`.
- `list_available_contexts()` opens every `contexts/*.md` directly in `research_agent/context.py:318-329`.
- `auto_detect_context()` returns `CONTEXTS_DIR / f"{name}.md"` for the selected entry without re-validating the resolved target in `research_agent/context.py:392-405`.
- The selected path is then loaded by the agent in `research_agent/agent.py:421-429`.
- MCP exposes previews from `list_available_contexts()` through `research_agent/mcp_server.py:293-306`.

Confirmed behavior:

- A symlinked `contexts/leak.md` pointing outside `contexts/` is previewed by `list_available_contexts()` and fully loaded by `load_full_context()`.

Why this matters:

- The code intends `contexts/` to be an operator-controlled boundary.
- The current protections are strong for string traversal, but weak for symlink traversal.
- In the default local setup this requires local filesystem manipulation, so this is not critical; in shared or hosted usage it becomes materially more important.

Recommended fix:

- Enforce resolved-path containment for context discovery, preview, auto-detect selection, and full loading.
- Ignore or reject symlinked context files whose resolved target is outside `contexts/`.
- Add tests for symlinked files under `contexts/`.

### RA-SEC-003: Repo-local containment for `reports/` and `reports/meta/` is symlink-sensitive

Impact: a symlinked `reports/` or `reports/meta/` root can redirect auto-save, `get_report()`, and critique-history loading outside the repo-local directories that the code intends to use.

Evidence:

- Auto-save paths are constructed under `REPORTS_DIR` in `research_agent/report_store.py:35-40`.
- `atomic_write()` resolves the target path and only rejects a symlink at the final leaf path in `research_agent/safe_io.py:28-31`.
- `_validate_report_filename()` anchors containment to `REPORTS_DIR.resolve()` in `research_agent/mcp_server.py:324-329`.
- `load_critique_history()` globs and reads `reports/meta/critique-*.yaml` directly in `research_agent/context.py:531-543`.
- The agent auto-loads critique history in standard/deep runs in `research_agent/agent.py:434-439`.

Confirmed behavior:

- A symlinked `reports/` root allows `_validate_report_filename()` to accept a file outside the repo-local `reports/` directory.
- Symlinked `reports/meta/critique-*.yaml` files are read and summarized by `load_critique_history()`.

Why this matters:

- The repo docs and code structure imply repo-local containment for generated reports and critique metadata.
- The current implementation protects against string traversal but not against base-directory symlink redirection.
- This is primarily a local/shared-environment hardening issue, so severity is lower than a remotely triggerable boundary bypass.

Recommended fix:

- Treat the literal repo-local `reports/` and `reports/meta/` directories as containment roots, not `resolve()`d symlink targets.
- Reject or ignore symlinked base directories and symlinked critique files that resolve outside their literal roots.
- Add regression tests for symlinked `reports/` and `reports/meta/`.

## Low Severity

### RA-SEC-004: Cascade fallback may disclose internal hostnames to third parties

Impact: a hostname that looks public but resolves to a private/internal IP may still be sent to Jina Reader or Tavily Extract, even though direct fetch would block it.

Evidence:

- `_is_internal_url()` only checks scheme, explicit blocked hosts, and literal IP strings in `research_agent/cascade.py:42-66`.
- `cascade_recover()` forwards all URLs that pass `_is_internal_url()` to Jina/Tavily in `research_agent/cascade.py:88-105`.
- The direct fetch path performs DNS resolution and pinned-IP validation in `research_agent/fetch.py:114-203` and `research_agent/fetch.py:260-275`.

Why this matters:

- This is not a direct SSRF-to-internal-service issue because the direct fetch path is stronger.
- It is still a confidentiality issue: internal URL patterns or private hostnames could be disclosed to external fallback providers.

Recommended fix:

- Reuse the existing SSRF-safe hostname validation before forwarding URLs to Jina Reader or Tavily Extract.
- Add tests covering hostnames that resolve to private addresses, not just literal private IPs.

## Strengths Confirmed

- Direct fetch SSRF protections are layered and well-placed in `research_agent/fetch.py:114-203` and `research_agent/fetch.py:255-385`.
- Redirect targets are revalidated hop-by-hop in `research_agent/fetch.py:269-280`.
- Context-name traversal defenses are present for explicit `--context` names in `research_agent/context.py:229-244`.
- MCP report retrieval rejects traversal characters, non-`.md` names, and out-of-root resolved paths in `research_agent/mcp_server.py:310-329`.
- The console MCP entrypoint refuses non-loopback HTTP binds in `research_agent/mcp_server.py:352-375`.

## Not Elevated To Findings

- `max_sources` is currently exposed through public APIs but not actually applied by `ResearchAgent.__init__()` in `research_agent/agent.py:62-94`. That makes prior “cost amplification through max_sources override” claims overstated in the current tree. It is a correctness/documentation issue more than a security bug.
- The programmatic `mcp` object can still be embedded and run by external code without going through `main()`. That is a deployment footgun, but not a vulnerability in the shipped `research-agent-mcp` console entrypoint.

## Suggested Fix Order

1. Fix prompt URL sanitization and add tests.
2. Enforce symlink-safe containment for `contexts/`.
3. Enforce symlink-safe containment for `reports/` and `reports/meta/`.
4. Reuse fetch-style hostname safety before cascade fallback forwarding.

## Three Questions

1. Hardest judgment call in this review?
Calibrating the symlink findings. They are real boundary bypasses, but their severity is materially lower in this repo’s default single-user CLI deployment than it would be in a shared service.

2. What did you consider flagging but chose not to, and why?
I considered elevating the programmatic `mcp` object exposure to a primary finding, but the shipped console entrypoint already enforces loopback-only HTTP binding, and the weaker path requires embedding misuse by another developer.

3. What might this review have missed?
Provider-specific LLM prompt-parsing quirks and OS-specific symlink edge cases beyond the reproduced macOS behavior. The review is strong on repo-local controls, but it does not replace live adversarial testing against external providers.
