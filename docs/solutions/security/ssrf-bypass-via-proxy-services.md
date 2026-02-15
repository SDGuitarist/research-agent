---
title: "SSRF Bypass via Proxy Services in Cascade Fallback"
date: 2026-02-13
category: security
tags: [ssrf, cascade, jina-reader, tavily-extract, httpx, toctou]
module: cascade.py, fetch.py
symptoms: "No symptoms — silent bypass discovered in security review"
severity: high
summary: "SSRF protection on main fetch path does not cover cascade fallback paths (Jina Reader, Tavily Extract), allowing private IP access through proxy services. Redirect-following also creates TOCTOU bypass."
---

# SSRF Bypass via Proxy Services in Cascade Fallback

**Security Review** | 2026-02-13

## Problem

The research agent has two independent bypass vectors that defeat its SSRF protection.

### Vector 1: Proxy Service Bypass

`fetch.py` validates every URL through `_is_safe_url()` before making HTTP requests. This function checks the scheme, hostname, and performs DNS resolution to block private IPs (`169.254.169.254`, `10.x.x.x`, `127.0.0.1`, etc.).

However, `cascade.py` was added as a fallback layer for URLs that fail direct fetch. It sends URLs to two external proxy services **without any SSRF checks**:

1. **Jina Reader** (`_fetch_via_jina`): Constructs `https://r.jina.ai/{url}` and sends it via httpx. A malicious URL like `http://169.254.169.254/latest/meta-data/` gets forwarded to Jina's servers, which fetch it on our behalf and return the content. The SSRF protection in `fetch.py` is never consulted.

2. **Tavily Extract** (`_fetch_via_tavily_extract`): Passes URLs directly to `client.extract(urls=urls[:20])`. Tavily's servers fetch those URLs. Again, no local validation occurs first.

The attack path: an attacker controls a URL that appears in search results (or is injected into the pipeline). Direct fetch fails (the SSRF check in `fetch.py` blocks it). The URL then enters `cascade_recover()` as a "failed URL," where it is forwarded to Jina or Tavily without validation. The proxy service fetches the private resource, and the content flows back into the pipeline.

### Vector 2: Redirect TOCTOU (Time-of-Check-Time-of-Use)

Both `fetch.py` and `cascade.py` create httpx clients with `follow_redirects=True`:

```python
# fetch.py line 232-234
async with httpx.AsyncClient(
    timeout=timeout, follow_redirects=True, ...
) as client:

# cascade.py line 97-98
async with httpx.AsyncClient(
    timeout=JINA_TIMEOUT, follow_redirects=True
) as client:
```

In `fetch.py`, `_is_safe_url()` validates the initial URL before the request. But if that URL returns a 301/302 redirect to a private IP (e.g., `http://safe-looking.com` redirects to `http://169.254.169.254/`), httpx follows the redirect automatically. The SSRF check ran against `safe-looking.com`, not the redirect target.

This is a classic TOCTOU vulnerability: the time of check (DNS resolution of the original hostname) differs from the time of use (following the redirect to a different host).

## Root Cause

Architectural: the SSRF validation in `_is_safe_url()` is private to `fetch.py` (prefixed with `_`). When `cascade.py` was added as a new code path that forwards URLs, it had no access to and no awareness of the validation logic. There was no shared URL safety module, so the safety check was silently skipped.

The redirect issue is a separate gap: `_is_safe_url()` only validates the initial URL, but httpx's redirect-following happens inside the HTTP client, after the check has already passed.

## Solution (Planned)

### Step 1: Extract shared URL validation

Move `_is_safe_url()`, `_is_private_ip()`, and `_resolve_and_validate_host()` from `fetch.py` into a shared module (e.g., `url_safety.py`). Keep them importable by both `fetch.py` and `cascade.py`.

```python
# research_agent/url_safety.py
def is_safe_url(url: str) -> bool: ...
def is_private_ip(ip_str: str) -> bool: ...
def resolve_and_validate_host(hostname: str, port: int = 443) -> bool: ...
```

### Step 2: Gate cascade paths

Add validation before each proxy call in `cascade.py`:

```python
from .url_safety import is_safe_url

async def cascade_recover(failed_urls, all_results):
    # Filter out unsafe URLs before any proxy forwarding
    safe_urls = [u for u in failed_urls if is_safe_url(u)]
    unsafe_count = len(failed_urls) - len(safe_urls)
    if unsafe_count:
        logger.warning(f"Blocked {unsafe_count} unsafe URLs from cascade recovery")
    ...
```

### Step 3: Add redirect validation via httpx event hooks

Use httpx's event hook system to validate redirect targets before following them:

```python
async def _check_redirect(response: httpx.Response) -> None:
    """Validate redirect targets to prevent SSRF via redirect."""
    if response.is_redirect:
        location = response.headers.get("location", "")
        if location and not is_safe_url(location):
            raise httpx.TooManyRedirects(
                f"Redirect to unsafe URL blocked: {location}"
            )

client = httpx.AsyncClient(
    follow_redirects=True,
    event_hooks={"response": [_check_redirect]},
)
```

Apply this to both `fetch.py` and `cascade.py` httpx clients.

## Prevention

1. **Shared URL safety module.** Any module that accepts, forwards, or proxies URLs must import from a single `url_safety.py`. Never duplicate SSRF checks inline.

2. **Code review checklist item.** When reviewing PRs that add new HTTP code paths, external API calls, or proxy integrations, explicitly verify: "Does this path run through `is_safe_url()` before the URL reaches any network call?"

3. **Redirect validation by default.** Never use `follow_redirects=True` without an event hook that validates redirect targets. Consider a shared httpx client factory that includes the redirect hook automatically.

4. **Treat proxy services as amplifiers.** A URL forwarded to Jina Reader or Tavily Extract has the same threat model as a URL fetched directly. Proxy services execute the request on their infrastructure, which may have access to resources your application cannot directly reach. Validate before forwarding, not after.

## Key Lesson

Every new code path that touches external URLs needs the same safety checks as the primary path. When you add a proxy service, CDN, or API fallback, it inherits the same threat model as direct HTTP fetching. The `cascade.py` module was designed as a "fallback for failed fetches," but from a security perspective, it is an independent fetch path that skipped the security gate.

## Related Documentation

- `research_agent/fetch.py` -- Primary fetch path with `_is_safe_url()` validation
- `research_agent/cascade.py` -- Fallback path missing validation (lines 91-126, 136-168)
- [`docs/solutions/logic-errors/adversarial-verification-pipeline.md`](../logic-errors/adversarial-verification-pipeline.md) -- Cycle 16: centralized utility audit pattern (same principle applies here)
- `LESSONS_LEARNED.md` -- Full cycle history
