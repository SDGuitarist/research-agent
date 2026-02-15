---
status: pending
priority: p1
issue_id: "022"
tags: [code-review, security, ssrf]
dependencies: []
---

# SSRF Bypass via HTTP Redirect to Internal Network

## Problem Statement

`fetch.py` validates URLs against internal networks via `_is_safe_url()` BEFORE the HTTP request, but httpx is configured with `follow_redirects=True` (line 237). An attacker-controlled URL could pass the pre-flight SSRF check and then redirect to an internal resource (e.g., `http://169.254.169.254/latest/meta-data/` on cloud instances). The same issue exists in `cascade.py` line 115 (Jina Reader requests).

## Findings

- **Source:** Security Sentinel agent
- **Location:** `research_agent/fetch.py:237`, `research_agent/cascade.py:115`
- **Evidence:** `follow_redirects=True` with no post-redirect validation

## Proposed Solutions

### Option A: Redirect validation hook (Recommended)
Add an httpx event hook that re-validates each redirect target against `_is_safe_url()`.
- **Pros:** Clean, framework-supported
- **Cons:** Requires async hook implementation
- **Effort:** Medium (1-2 hours)

### Option B: Disable auto-redirects, follow manually
Set `follow_redirects=False` and manually follow redirects with validation at each hop.
- **Pros:** Full control
- **Cons:** More code to maintain
- **Effort:** Medium (2-3 hours)

## Acceptance Criteria

- [ ] Redirect targets are validated against `_is_safe_url()` before following
- [ ] Both `fetch.py` and `cascade.py` are protected
- [ ] Test: redirect to 127.0.0.1 is blocked
- [ ] Test: redirect to public IP is allowed
