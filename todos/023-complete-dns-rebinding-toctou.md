---
status: ready
priority: p1
issue_id: "023"
tags: [code-review, security, ssrf, dns]
dependencies: []
---

# DNS Rebinding / TOCTOU Gap in SSRF Protection

## Problem Statement

`fetch.py` resolves DNS and validates IPs in `_resolve_and_validate_host()` (lines 104-131), but httpx performs its own independent DNS resolution when connecting. An attacker with a DNS server could use rebinding (low TTL, first resolve to public IP, second resolve to 127.0.0.1) to bypass SSRF protection entirely.

## Findings

- **Source:** Security Sentinel agent
- **Location:** `research_agent/fetch.py:104-131`
- **Evidence:** DNS resolved once for validation, but httpx re-resolves independently for connection

## Proposed Solutions

### Option A: Pin resolved IPs for httpx (Recommended)
Pass the pre-validated IPs directly to httpx via a custom transport/resolver, bypassing DNS for the actual connection.
- **Pros:** Eliminates the TOCTOU gap entirely
- **Cons:** Requires custom httpx transport
- **Effort:** High (2-4 hours)

### Option B: Validate post-connection
Check the connected IP address after the response is received.
- **Pros:** Simpler implementation
- **Cons:** Request already sent by the time we check
- **Effort:** Low (1 hour)

## Acceptance Criteria

- [ ] The IP used for the actual connection matches the pre-validated IP
- [ ] DNS rebinding attack is blocked
- [ ] Existing SSRF tests still pass
