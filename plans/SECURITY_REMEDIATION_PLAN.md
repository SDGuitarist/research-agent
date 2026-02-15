# Security Remediation Plan

**Date:** 2026-02-13
**Source:** Security audit (security-sentinel agent)
**Status:** In Progress

## Completed

### C-1: API Key Exposure
- [x] Restricted `.env` to `chmod 600` (owner-only read/write)
- [x] Updated `.env.example` to document both required keys
- [ ] **YOU MUST DO:** Rotate `ANTHROPIC_API_KEY` at https://console.anthropic.com/settings/keys
- [ ] **YOU MUST DO:** Rotate `TAVILY_API_KEY` at https://app.tavily.com/home

---

## Next Cycle: High-Priority Fixes

### H-2: SSRF Bypass in Cascade (Jina Reader + Tavily Extract)

**Problem:** `cascade.py` sends URLs to Jina/Tavily without the SSRF checks that `fetch.py` applies. Internal/cloud metadata endpoints could be reached.

**Fix:**
1. Extract `_is_safe_url()` and `_resolve_and_validate_host()` from `fetch.py` into a shared module (e.g., `url_safety.py` or add to `sanitize.py`)
2. Call `_is_safe_url()` at the top of `_jina_single()` (cascade.py ~line 97) — return `None` if unsafe
3. Call `_is_safe_url()` on each URL before passing to Tavily Extract (cascade.py ~line 139)
4. Add tests for private IPs, localhost, and cloud metadata URLs being blocked in cascade

**Files to modify:**
- `research_agent/fetch.py` — extract shared functions
- `research_agent/cascade.py` — add validation calls
- `tests/` — add cascade SSRF tests

---

### H-3: SSRF via Redirect (follow_redirects=True)

**Problem:** `fetch.py:234` and `cascade.py:90` use `follow_redirects=True`. A safe URL can HTTP-redirect to a private IP, bypassing the initial check (TOCTOU).

**Fix:**
1. Add an httpx event hook that validates each redirect target against `_is_safe_url()`:
   ```python
   def _validate_redirect(request):
       if not _is_safe_url(str(request.url)):
           raise httpx.TooManyRedirects("Redirect to unsafe URL blocked")
   ```
2. Apply the hook to all `httpx.AsyncClient` instances in `fetch.py` and `cascade.py`
3. Add tests: mock a redirect from safe URL → private IP, verify it's blocked

**Files to modify:**
- `research_agent/fetch.py` — add event hook to AsyncClient
- `research_agent/cascade.py` — add event hook to AsyncClient
- `tests/` — add redirect SSRF tests

---

### H-1: Command Injection via subprocess.run

**Problem:** `main.py:279` passes user-provided `-o` path to macOS `open` without validation.

**Fix:**
1. Validate output path before passing to `subprocess.run`:
   ```python
   if output_path.suffix == ".md" and output_path.exists():
       subprocess.run(["open", str(output_path)])
   ```
2. Optionally: resolve path and check it's within the working directory

**Files to modify:**
- `main.py` — add validation before `subprocess.run`
- `tests/` — add test for path validation

---

## Later Cycles: Medium-Priority

These can be addressed after the high-priority fixes:

| ID  | Fix | Effort |
|-----|-----|--------|
| M-1 | Replace 10 bare `except Exception` with specific types | Medium (spread across files) |
| M-2 | Pin dependencies, add `pip-audit` | Small |
| M-3 | Validate `-o` path stays within allowed directory | Small |
| M-4 | Add `MAX_CASCADE_CONTENT_SIZE` check in cascade.py | Small |
| M-5 | Enhance `sanitize_content()` with Unicode/null byte cleanup | Small |
