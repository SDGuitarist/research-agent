---
status: ready
priority: p2
issue_id: "025"
tags: [code-review, security, ssrf]
dependencies: []
---

# Jina Reader Cascade Bypasses SSRF Validation

## Problem Statement

URLs blocked by SSRF validation in `fetch.py` end up in the `failed_urls` list and are forwarded to `cascade_recover()`, which sends them to Jina Reader (`https://r.jina.ai/{url}`). This leaks internal URL patterns to a third-party service.

## Findings

- **Source:** Security Sentinel agent
- **Location:** `research_agent/agent.py` (failed URL forwarding), `research_agent/cascade.py:108-143`

## Proposed Solutions

### Option A: Filter SSRF-blocked URLs from cascade (Recommended)
Track which URLs were blocked by `_is_safe_url()` and exclude them from cascade recovery.
- **Effort:** Small (1 hour)

## Acceptance Criteria

- [ ] URLs blocked by SSRF check are not forwarded to cascade recovery
- [ ] Test: SSRF-blocked URL does not appear in Jina Reader request
