---
title: "Domain Matching Substring Bypass in Cascade Fallback"
date: 2026-02-15
category: security
tags: [domain-matching, cascade, substring-bypass, endswith]
module: cascade.py
symptoms: "No runtime symptoms — discovered during code review. Malicious domains like evilyelp.com would match yelp.com checks."
severity: medium
summary: "Using host.endswith('domain.com') for domain matching allows substring bypasses. Fix: require dot prefix or exact match."
---

# Domain Matching Substring Bypass in Cascade Fallback

**Code Review** | 2026-02-15 | Commit `dffbbb1`

## Problem

In `cascade.py`, certain domains receive special handling during content extraction (e.g., Yelp pages need different parsing). The domain check used Python's `str.endswith()` with a bare domain:

```python
# BAD — substring match allows spoofing
if host.endswith("yelp.com"):
    # special handling for Yelp pages
    ...
```

This matches any hostname that ends with `yelp.com`, including attacker-controlled domains like `evilyelp.com`, `not-yelp.com`, or `phishingyelp.com`. An attacker could register such a domain and have their content receive the trusted Yelp code path, potentially bypassing content validation or extraction logic.

## Root Cause

`str.endswith("yelp.com")` is a substring match, not a domain boundary match. DNS domains are dot-separated hierarchical labels. The string `evilyelp.com` ends with `yelp.com` at the string level, but it is a completely unrelated domain at the DNS level. The check fails to enforce a domain boundary (the `.` separator).

This is a well-known class of bug. The same pattern causes security issues in cookie scoping, CORS origin checks, and certificate validation whenever substring matching replaces proper domain parsing.

## Solution

Require either a dot prefix (indicating a subdomain like `www.yelp.com`) or an exact match (the bare domain `yelp.com`):

```python
# GOOD — enforces domain boundary
if host.endswith(".yelp.com") or host == "yelp.com":
    # special handling for Yelp pages
    ...
```

This correctly matches:
- `yelp.com` (exact)
- `www.yelp.com` (subdomain)
- `m.yelp.com` (subdomain)

And correctly rejects:
- `evilyelp.com` (different domain)
- `not-yelp.com` (different domain)

Applied to every `endswith()` domain check in `cascade.py`.

## Prevention

**General rule:** Never use `host.endswith("domain.com")` for domain matching. Always use this two-part pattern:

```python
def matches_domain(host: str, domain: str) -> bool:
    """Check if host is exactly domain or a subdomain of it."""
    return host == domain or host.endswith(f".{domain}")
```

If the project accumulates more domain checks, extract this into a shared utility. For now, the inline two-part check is sufficient and clear.

**Code review checkpoint:** Any PR that adds `endswith()` on a hostname should be flagged. The bare `endswith("domain.com")` pattern is always wrong for domain matching.

## Cross-References

- [`docs/solutions/security/ssrf-bypass-via-proxy-services.md`](ssrf-bypass-via-proxy-services.md) -- Related cascade.py security issue (SSRF bypass via proxy services)
- `research_agent/cascade.py` -- Module where the fix was applied
- `LESSONS_LEARNED.md` -- Full cycle history
