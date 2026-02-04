# Python Research Agent Failure Modes Catalog

A comprehensive catalog of failure modes for Python research agents that perform web searches, content scraping, LLM API calls, and markdown report generation.

---

## Table of Contents

1. [Network Failures](#1-network-failures)
2. [Search API Failures](#2-search-api-failures)
3. [Web Scraping Failures](#3-web-scraping-failures)
4. [LLM API Failures (Anthropic)](#4-llm-api-failures-anthropic)
5. [Content Processing Failures](#5-content-processing-failures)
6. [Output Failures](#6-output-failures)

---

## 1. Network Failures

### 1.1 Connection Timeout

| Aspect | Details |
|--------|---------|
| **What triggers it** | Server takes too long to accept connection; network congestion; server overload; firewall blocking |
| **How to detect it** | `httpx.ConnectTimeout` or `requests.ConnectTimeout` exception |
| **Handling strategy** | Retry with exponential backoff (1s, 2s, 4s). Set reasonable connect timeout (5-10s). After 3 retries, log and skip URL. |

```python
import httpx

try:
    response = httpx.get(url, timeout=httpx.Timeout(connect=5.0, read=30.0))
except httpx.ConnectTimeout:
    # Safe to retry - connection was never established
    logger.warning(f"Connection timeout for {url}, retrying...")
```

### 1.2 Read Timeout

| Aspect | Details |
|--------|---------|
| **What triggers it** | Server accepts connection but response data arrives too slowly; large files; slow servers |
| **How to detect it** | `httpx.ReadTimeout` or `requests.ReadTimeout` exception |
| **Handling strategy** | Increase read timeout for known slow endpoints. Retry once. Consider streaming for large responses. |

```python
except httpx.ReadTimeout:
    # Connection established, but server stopped sending data
    logger.warning(f"Read timeout for {url}")
    # May indicate server issues - retry with longer timeout
```

### 1.3 DNS Resolution Failure

| Aspect | Details |
|--------|---------|
| **What triggers it** | Invalid hostname; DNS server unavailable; network misconfiguration; typos in URLs |
| **How to detect it** | `socket.gaierror` with error codes: `-2` (EAI_NONAME - doesn't exist), `-3` (EAI_AGAIN - temporary), `-5` (EAI_NOADDR - no address) |
| **Handling strategy** | For `-3` (temporary): retry after 1-2 seconds. For `-2` (doesn't exist): log and skip. Validate URLs before requests. |

```python
import socket

try:
    response = httpx.get(url)
except httpx.ConnectError as e:
    if isinstance(e.__cause__, socket.gaierror):
        errno = e.__cause__.args[0]
        if errno == socket.EAI_AGAIN:  # -3: Temporary failure
            logger.info(f"Temporary DNS failure for {url}, retrying...")
            time.sleep(2)
            # Retry
        elif errno == socket.EAI_NONAME:  # -2: Host doesn't exist
            logger.error(f"Invalid hostname in {url}")
            # Don't retry - URL is bad
```

### 1.4 Connection Refused

| Aspect | Details |
|--------|---------|
| **What triggers it** | Server not running; wrong port; firewall blocking; server at capacity |
| **How to detect it** | `httpx.ConnectError` with `ConnectionRefusedError` as cause |
| **Handling strategy** | Retry 2-3 times with backoff. May indicate temporary server issue or permanent unavailability. |

```python
except httpx.ConnectError as e:
    if isinstance(e.__cause__, ConnectionRefusedError):
        logger.warning(f"Connection refused for {url}")
        # Server explicitly rejected - may be down or blocking
```

### 1.5 SSL/TLS Certificate Errors

| Aspect | Details |
|--------|---------|
| **What triggers it** | Expired certificate; self-signed certificate; hostname mismatch; missing intermediate certificates; corporate proxy intercepting traffic; outdated TLS version |
| **How to detect it** | `ssl.SSLCertVerificationError`, `httpx.ConnectError` with SSL cause, `requests.exceptions.SSLError` |
| **Handling strategy** | **Never disable verification in production**. Update certifi: `pip install --upgrade certifi`. For corporate proxies, add company CA to trust store. For self-signed in dev only: use custom CA bundle. |

```python
import ssl
import certifi

# Proper approach: Use updated certificates
client = httpx.Client(verify=certifi.where())

# For corporate environments with custom CA
client = httpx.Client(verify="/path/to/corporate-ca-bundle.pem")

# DANGEROUS - development only, never in production
# client = httpx.Client(verify=False)

try:
    response = client.get(url)
except httpx.ConnectError as e:
    if "SSL" in str(e) or "certificate" in str(e).lower():
        logger.error(f"SSL error for {url}: {e}")
        # Log for investigation, don't auto-bypass
```

### 1.6 Connection Pool Exhaustion

| Aspect | Details |
|--------|---------|
| **What triggers it** | Too many concurrent requests; connections not being released; slow servers holding connections |
| **How to detect it** | `httpx.PoolTimeout` exception |
| **Handling strategy** | Configure appropriate pool limits. Use context managers to ensure connection release. Implement request queuing. |

```python
# Configure connection limits
limits = httpx.Limits(
    max_connections=50,
    max_keepalive_connections=10
)
timeout = httpx.Timeout(pool=5.0)  # Wait up to 5s for pool

async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
    try:
        response = await client.get(url)
    except httpx.PoolTimeout:
        logger.warning("Connection pool exhausted, queuing request...")
```

---

## 2. Search API Failures

### 2.1 Rate Limiting (429)

| Aspect | Details |
|--------|---------|
| **What triggers it** | Exceeding API quota; too many requests per second/minute; burst traffic |
| **How to detect it** | HTTP 429 status code; `Retry-After` header; API-specific error messages |
| **Handling strategy** | Implement exponential backoff. Respect `Retry-After` header. Use request caching. Queue requests with rate limiter. |

```python
import time

def search_with_rate_limit(query, max_retries=5):
    for attempt in range(max_retries):
        response = search_api.search(query)

        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 2 ** attempt))
            logger.warning(f"Rate limited, waiting {retry_after}s...")
            time.sleep(retry_after)
            continue

        return response

    raise RateLimitExceeded(f"Still rate limited after {max_retries} attempts")
```

### 2.2 Empty Results

| Aspect | Details |
|--------|---------|
| **What triggers it** | No matching content; overly specific query; regional restrictions; API returning empty for unclear reasons |
| **How to detect it** | Response returns empty list/dict; `organic_results` key is empty; zero result count |
| **Handling strategy** | Try query reformulation (broaden terms, remove quotes). Try different search engines. Log for analysis. Return partial results if available. |

```python
def robust_search(query):
    results = search_api.search(query)

    if not results.get('organic_results'):
        logger.info(f"No results for '{query}', trying broader search...")

        # Strategy 1: Remove quotes
        broader_query = query.replace('"', '')
        results = search_api.search(broader_query)

        if not results.get('organic_results'):
            # Strategy 2: Use fewer terms
            terms = query.split()[:3]
            results = search_api.search(' '.join(terms))

    return results
```

### 2.3 API Key Invalid/Expired

| Aspect | Details |
|--------|---------|
| **What triggers it** | Expired subscription; revoked key; typo in key; wrong environment variable |
| **How to detect it** | HTTP 401/403; specific error message about authentication |
| **Handling strategy** | Validate key on startup. Alert immediately on auth failure. Have fallback keys for redundancy. Never expose keys in logs. |

```python
class SearchAPIError(Exception):
    pass

def validate_api_key():
    """Call on startup to fail fast"""
    try:
        # Most APIs have a lightweight endpoint for validation
        response = search_api.account_info()
        if response.get('error'):
            raise SearchAPIError(f"API key invalid: {response['error']}")
    except Exception as e:
        logger.critical(f"Search API authentication failed: {e}")
        raise
```

### 2.4 Malformed/Unexpected Response

| Aspect | Details |
|--------|---------|
| **What triggers it** | API version change; partial response due to timeout; server error returning HTML instead of JSON; SerpAPI empty response bug |
| **How to detect it** | `json.JSONDecodeError`; missing expected keys; wrong data types |
| **Handling strategy** | Validate response structure. Handle gracefully with defaults. Log unexpected formats for investigation. |

```python
def parse_search_response(response):
    try:
        data = response.json()
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON response: {response.text[:200]}")
        return {'organic_results': [], 'error': 'Invalid response format'}

    # Validate expected structure
    if 'search_metadata' not in data:
        logger.warning("Missing search_metadata, response may be incomplete")

    # Check for API-level errors
    if error := data.get('error'):
        logger.error(f"Search API error: {error}")
        return {'organic_results': [], 'error': error}

    return data
```

### 2.5 Quota Exceeded

| Aspect | Details |
|--------|---------|
| **What triggers it** | Monthly/daily search limit reached; budget exhausted |
| **How to detect it** | Specific error codes (varies by provider); account status endpoint |
| **Handling strategy** | Monitor usage proactively. Alert at 80% threshold. Have fallback search providers. Cache aggressively. |

```python
# Check quota before expensive operations
def check_quota():
    usage = search_api.get_usage()
    remaining = usage['monthly_limit'] - usage['monthly_used']

    if remaining < 100:
        logger.warning(f"Low search quota: {remaining} remaining")

    if remaining <= 0:
        raise QuotaExceeded("Monthly search quota exhausted")
```

---

## 3. Web Scraping Failures

### 3.1 HTTP 403 Forbidden (Bot Detection)

| Aspect | Details |
|--------|---------|
| **What triggers it** | Missing/wrong User-Agent; detected automation fingerprints; IP reputation; behavioral analysis; Cloudflare/Akamai protection |
| **How to detect it** | HTTP 403 status; Cloudflare challenge page; "Access Denied" content |
| **Handling strategy** | Use realistic User-Agent. Rotate IPs/proxies. Add realistic headers. For JS challenges, consider headless browsers (Playwright). Rate limit requests. |

```python
REALISTIC_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

def fetch_with_stealth(url):
    response = httpx.get(url, headers=REALISTIC_HEADERS)

    if response.status_code == 403:
        # Check if it's a challenge page
        if 'cloudflare' in response.text.lower():
            logger.warning(f"Cloudflare challenge for {url}")
            # Need headless browser or skip
            raise CloudflareBlocked(url)

        logger.warning(f"403 Forbidden for {url}")
        raise AccessDenied(url)

    return response
```

### 3.2 HTTP 429 Too Many Requests

| Aspect | Details |
|--------|---------|
| **What triggers it** | Request rate too high; detected scraping patterns; single IP making too many requests |
| **How to detect it** | HTTP 429 status; rate limit headers; redirect to verification page |
| **Handling strategy** | Implement delays between requests (1-5s). Use exponential backoff. Rotate IPs. Respect robots.txt crawl-delay. |

```python
import asyncio
from collections import defaultdict

class RateLimitedFetcher:
    def __init__(self, requests_per_second=0.5):
        self.min_delay = 1.0 / requests_per_second
        self.last_request = defaultdict(float)

    async def fetch(self, url):
        domain = urlparse(url).netloc

        # Enforce per-domain rate limiting
        elapsed = time.time() - self.last_request[domain]
        if elapsed < self.min_delay:
            await asyncio.sleep(self.min_delay - elapsed)

        self.last_request[domain] = time.time()

        response = await self.client.get(url)

        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            logger.warning(f"Rate limited by {domain}, waiting {retry_after}s")
            await asyncio.sleep(retry_after)
            return await self.fetch(url)  # Retry

        return response
```

### 3.3 JavaScript-Rendered Content

| Aspect | Details |
|--------|---------|
| **What triggers it** | SPA (React, Vue, Angular); content loaded via AJAX; infinite scroll; dynamic rendering |
| **How to detect it** | Empty or minimal HTML; presence of framework markers; content differs from browser view |
| **Handling strategy** | Use headless browser (Playwright, Selenium). Check for API endpoints returning JSON. Use services like Browserless. |

```python
from playwright.async_api import async_playwright

async def fetch_js_rendered(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until='networkidle')
            content = await page.content()
            return content
        finally:
            await browser.close()

def needs_js_rendering(response):
    """Heuristic to detect JS-only pages"""
    indicators = [
        '<div id="root"></div>',  # React
        '<div id="app"></div>',   # Vue
        'ng-app',                  # Angular
        '__NEXT_DATA__',          # Next.js
    ]

    content = response.text
    # Very little text content but JS framework markers
    text_content = BeautifulSoup(content, 'html.parser').get_text()

    if len(text_content.strip()) < 100 and any(ind in content for ind in indicators):
        return True
    return False
```

### 3.4 Paywall Detection

| Aspect | Details |
|--------|---------|
| **What triggers it** | Premium content; article limits; subscription-only sites |
| **How to detect it** | Truncated content; paywall modal markers; subscription prompts; HTTP 402 |
| **Handling strategy** | Detect and skip. Try archive services. Extract available preview. Mark as paywalled in results. |

```python
PAYWALL_INDICATORS = [
    'subscribe to continue',
    'subscription required',
    'premium content',
    'paywall',
    'sign in to read',
    'members only',
    'article limit reached',
]

def detect_paywall(content):
    content_lower = content.lower()

    for indicator in PAYWALL_INDICATORS:
        if indicator in content_lower:
            return True

    # Check for common paywall CSS classes
    soup = BeautifulSoup(content, 'html.parser')
    paywall_classes = soup.find_all(class_=lambda c: c and 'paywall' in c.lower())

    return len(paywall_classes) > 0
```

### 3.5 CAPTCHA Challenges

| Aspect | Details |
|--------|---------|
| **What triggers it** | Suspicious traffic patterns; bot detection systems; rate limits; Cloudflare Turnstile |
| **How to detect it** | CAPTCHA markers in HTML; redirect to challenge page; specific response headers |
| **Handling strategy** | Reduce request rate. Use residential proxies. For critical needs, consider CAPTCHA-solving services. Often best to skip and try alternatives. |

```python
CAPTCHA_INDICATORS = [
    'captcha',
    'recaptcha',
    'hcaptcha',
    'challenge-form',
    'cf-turnstile',
    'g-recaptcha',
]

def detect_captcha(response):
    content = response.text.lower()

    for indicator in CAPTCHA_INDICATORS:
        if indicator in content:
            return True

    # Check for Cloudflare challenge
    if response.status_code == 403 and 'cf-ray' in response.headers:
        return True

    return False
```

### 3.6 Malformed HTML

| Aspect | Details |
|--------|---------|
| **What triggers it** | Poorly coded websites; truncated responses; server errors returning partial content |
| **How to detect it** | Parser errors; missing expected elements; BeautifulSoup warnings |
| **Handling strategy** | Use lenient parsers (html5lib). Handle missing elements gracefully. Validate extracted data. |

```python
from bs4 import BeautifulSoup
import warnings

def parse_html_safely(content):
    # html5lib is most lenient, handles badly broken HTML
    with warnings.catch_warnings(record=True) as w:
        soup = BeautifulSoup(content, 'html5lib')

        if w:
            logger.debug(f"Parser warnings: {[str(warning.message) for warning in w]}")

    return soup

def extract_with_fallbacks(soup, selectors):
    """Try multiple selectors, return first match"""
    for selector in selectors:
        try:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        except Exception as e:
            logger.debug(f"Selector {selector} failed: {e}")

    return None
```

### 3.7 Encoding Issues

| Aspect | Details |
|--------|---------|
| **What triggers it** | Incorrect charset declaration; mixed encodings; legacy Windows-1252 sites; missing BOM handling |
| **How to detect it** | Garbled characters (mojibake); `UnicodeDecodeError`; `?` or replacement characters in output |
| **Handling strategy** | Use `response.apparent_encoding`. Try encoding cascade (UTF-8 -> Windows-1252 -> Latin-1). Use chardet for detection. |

```python
import chardet

def decode_content_safely(response):
    # First, try the declared encoding
    try:
        return response.text
    except UnicodeDecodeError:
        pass

    # Try apparent encoding (chardet-based)
    response.encoding = response.apparent_encoding
    try:
        return response.text
    except UnicodeDecodeError:
        pass

    # Manual detection with chardet
    detected = chardet.detect(response.content)
    if detected['encoding']:
        try:
            return response.content.decode(detected['encoding'])
        except UnicodeDecodeError:
            pass

    # Fallback cascade
    for encoding in ['utf-8', 'windows-1252', 'latin-1']:
        try:
            return response.content.decode(encoding, errors='replace')
        except UnicodeDecodeError:
            continue

    # Last resort: decode with replacement characters
    return response.content.decode('utf-8', errors='replace')
```

---

## 4. LLM API Failures (Anthropic)

### 4.1 Rate Limiting (429)

| Aspect | Details |
|--------|---------|
| **What triggers it** | Exceeding requests per minute; token throughput limits; concurrent request limits |
| **How to detect it** | `anthropic.RateLimitError`; HTTP 429 status |
| **Handling strategy** | SDK auto-retries (2 retries default). Implement request queuing. Use exponential backoff. Monitor usage patterns. |

```python
import anthropic
from anthropic import RateLimitError

client = anthropic.Anthropic(
    max_retries=3  # Override default of 2
)

async def call_with_backoff(messages, max_attempts=5):
    for attempt in range(max_attempts):
        try:
            return client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=messages
            )
        except RateLimitError as e:
            if attempt == max_attempts - 1:
                raise

            wait_time = 2 ** attempt  # 1, 2, 4, 8, 16 seconds
            logger.warning(f"Rate limited, waiting {wait_time}s...")
            await asyncio.sleep(wait_time)
```

### 4.2 Context Length Exceeded

| Aspect | Details |
|--------|---------|
| **What triggers it** | Input tokens + max_tokens > model limit (200k for Claude 3); very long documents; accumulated conversation history |
| **How to detect it** | `anthropic.BadRequestError` with message containing "context limit" or "exceeds"; HTTP 400 |
| **Handling strategy** | Pre-calculate token count. Truncate/chunk long inputs. Summarize conversation history. Reduce max_tokens. |

```python
import anthropic

def estimate_tokens(text):
    """Rough estimate: ~4 chars per token for English"""
    return len(text) // 4

def truncate_to_fit(content, max_tokens=150000):
    """Truncate content to fit within context window"""
    estimated = estimate_tokens(content)

    if estimated <= max_tokens:
        return content

    # Truncate from the middle to preserve beginning and end
    char_limit = max_tokens * 4
    half = char_limit // 2

    truncated = content[:half] + "\n\n[... content truncated ...]\n\n" + content[-half:]
    logger.warning(f"Content truncated from {estimated} to ~{max_tokens} tokens")

    return truncated

def call_api_with_chunking(content, query):
    try:
        return client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": f"{query}\n\n{content}"}]
        )
    except anthropic.BadRequestError as e:
        if "context" in str(e).lower() and "limit" in str(e).lower():
            logger.warning("Context limit exceeded, truncating...")
            truncated = truncate_to_fit(content)
            return client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[{"role": "user", "content": f"{query}\n\n{truncated}"}]
            )
        raise
```

### 4.3 Content Filtering / Output Blocked

| Aspect | Details |
|--------|---------|
| **What triggers it** | Content violating usage policy; false positives on legitimate content (e.g., security discussions, medical info, license text) |
| **How to detect it** | `anthropic.BadRequestError` with "content filtering policy" message; `stop_reason: "content_filter"` |
| **Handling strategy** | Rephrase request. Add context about legitimate use. For false positives, contact Anthropic. Log for review. |

```python
def handle_content_filter(messages, attempt=0):
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=messages
        )

        if response.stop_reason == "content_filter":
            logger.warning("Response stopped due to content filter")
            return None, "content_filtered"

        return response, None

    except anthropic.BadRequestError as e:
        if "content filtering" in str(e).lower():
            logger.warning(f"Content filtered: {e}")

            if attempt == 0:
                # Try rephrasing
                modified = [{
                    **m,
                    "content": f"[Academic/Research context] {m['content']}"
                } for m in messages]
                return handle_content_filter(modified, attempt=1)

            return None, "content_filtered"
        raise
```

### 4.4 API Connection Errors

| Aspect | Details |
|--------|---------|
| **What triggers it** | Network issues; Anthropic service disruption; DNS failures; proxy issues |
| **How to detect it** | `anthropic.APIConnectionError` exception |
| **Handling strategy** | Auto-retry (SDK default). Check Anthropic status page. Implement circuit breaker for persistent failures. |

```python
import anthropic

try:
    response = client.messages.create(...)
except anthropic.APIConnectionError as e:
    logger.error(f"Cannot reach Anthropic API: {e.__cause__}")
    # Check if it's DNS, timeout, or connection refused
    cause = str(e.__cause__)

    if "timeout" in cause.lower():
        # Network slow, may resolve
        raise RetryableError("API timeout")
    elif "gaierror" in cause.lower():
        # DNS issue
        raise RetryableError("DNS resolution failed")
    else:
        # Connection refused or other
        raise ServiceUnavailable("Anthropic API unreachable")
```

### 4.5 Invalid Request Errors

| Aspect | Details |
|--------|---------|
| **What triggers it** | Invalid model name; malformed messages array; invalid parameter values; missing required fields |
| **How to detect it** | `anthropic.BadRequestError` (non-content-filter); HTTP 400 |
| **Handling strategy** | Validate inputs before calling. Log full error details. Fix and don't retry (not transient). |

```python
def validate_messages(messages):
    """Validate message format before API call"""
    if not messages:
        raise ValueError("Messages cannot be empty")

    for i, msg in enumerate(messages):
        if 'role' not in msg:
            raise ValueError(f"Message {i} missing 'role'")
        if msg['role'] not in ('user', 'assistant'):
            raise ValueError(f"Message {i} has invalid role: {msg['role']}")
        if 'content' not in msg:
            raise ValueError(f"Message {i} missing 'content'")
        if not msg['content']:
            raise ValueError(f"Message {i} has empty content")

    # First message must be from user
    if messages[0]['role'] != 'user':
        raise ValueError("First message must be from user")

try:
    validate_messages(messages)
    response = client.messages.create(...)
except anthropic.BadRequestError as e:
    logger.error(f"Invalid request: {e.status_code} - {e.message}")
    # Don't retry - fix the input
    raise
```

### 4.6 Server Errors (5xx)

| Aspect | Details |
|--------|---------|
| **What triggers it** | Anthropic infrastructure issues; overload; deployment issues |
| **How to detect it** | `anthropic.InternalServerError` (500), `anthropic.APIStatusError` with 5xx status |
| **Handling strategy** | Auto-retry with backoff (SDK handles this). For persistent 5xx, check status page and implement fallback. |

```python
try:
    response = client.messages.create(...)
except anthropic.InternalServerError:
    logger.error("Anthropic API internal error")
    # SDK will have already retried - this is persistent
    # Check status.anthropic.com
    raise ServiceDegraded("Anthropic API experiencing issues")
except anthropic.APIStatusError as e:
    if e.status_code >= 500:
        logger.error(f"Anthropic server error: {e.status_code}")
        raise ServiceDegraded(f"API error: {e.status_code}")
    raise
```

### 4.7 Malformed/Incomplete Responses

| Aspect | Details |
|--------|---------|
| **What triggers it** | Network interruption during streaming; max_tokens reached mid-sentence; API issues |
| **How to detect it** | `stop_reason: "max_tokens"` (truncated); incomplete JSON in response; unexpected structure |
| **Handling strategy** | Check stop_reason. For truncation, continue conversation or increase max_tokens. Validate response structure. |

```python
def process_response(response):
    if response.stop_reason == "max_tokens":
        logger.warning("Response truncated due to max_tokens limit")
        # May need to continue or increase limit
        return response.content[0].text, {"truncated": True}

    if response.stop_reason == "end_turn":
        # Normal completion
        return response.content[0].text, {"truncated": False}

    if response.stop_reason == "content_filter":
        return None, {"filtered": True}

    # Unexpected stop reason
    logger.warning(f"Unexpected stop_reason: {response.stop_reason}")
    return response.content[0].text, {"stop_reason": response.stop_reason}
```

---

## 5. Content Processing Failures

### 5.1 Empty Content

| Aspect | Details |
|--------|---------|
| **What triggers it** | Page requires authentication; content loaded via JS; soft 404; blocked access returning empty body |
| **How to detect it** | Empty response body; no text after HTML parsing; only boilerplate (nav, footer) |
| **Handling strategy** | Validate content length. Check for minimum text threshold. Log and skip empty pages. |

```python
def validate_content(html, min_text_length=100):
    soup = BeautifulSoup(html, 'html.parser')

    # Remove boilerplate
    for tag in soup.find_all(['nav', 'header', 'footer', 'script', 'style']):
        tag.decompose()

    text = soup.get_text(separator=' ', strip=True)

    if len(text) < min_text_length:
        raise EmptyContentError(f"Content too short: {len(text)} chars")

    return text
```

### 5.2 Non-Text Content (Binary Files)

| Aspect | Details |
|--------|---------|
| **What triggers it** | Link points to PDF, image, video, zip; Content-Type mismatch; dynamic file serving |
| **How to detect it** | Content-Type header; file extension; magic bytes |
| **Handling strategy** | Check Content-Type before downloading. Handle PDFs specially. Skip binary files. |

```python
SUPPORTED_CONTENT_TYPES = [
    'text/html',
    'text/plain',
    'application/xhtml+xml',
]

def fetch_text_content(url):
    # HEAD request first to check content type
    head = httpx.head(url, follow_redirects=True)
    content_type = head.headers.get('content-type', '').split(';')[0]

    if content_type == 'application/pdf':
        return fetch_and_extract_pdf(url)

    if content_type not in SUPPORTED_CONTENT_TYPES:
        raise UnsupportedContentType(f"Cannot process {content_type}")

    response = httpx.get(url)
    return response.text
```

### 5.3 Extremely Long Pages

| Aspect | Details |
|--------|---------|
| **What triggers it** | Forum threads; documentation pages; log files; data dumps |
| **How to detect it** | Content-Length header; response size after download; token count estimate |
| **Handling strategy** | Stream large responses. Truncate intelligently. Extract relevant sections only. |

```python
MAX_CONTENT_SIZE = 1_000_000  # 1MB
MAX_TOKENS_FOR_LLM = 100_000

def fetch_with_size_limit(url):
    with httpx.stream('GET', url) as response:
        chunks = []
        total_size = 0

        for chunk in response.iter_bytes():
            total_size += len(chunk)

            if total_size > MAX_CONTENT_SIZE:
                logger.warning(f"Content truncated at {MAX_CONTENT_SIZE} bytes")
                break

            chunks.append(chunk)

        return b''.join(chunks).decode('utf-8', errors='replace')

def prepare_for_llm(content):
    """Truncate content to fit LLM context"""
    estimated_tokens = len(content) // 4

    if estimated_tokens > MAX_TOKENS_FOR_LLM:
        # Keep beginning and end, which often have most info
        char_limit = MAX_TOKENS_FOR_LLM * 4
        half = char_limit // 2

        return (
            content[:half] +
            "\n\n[...middle content truncated for length...]\n\n" +
            content[-half:]
        )

    return content
```

### 5.4 Character Encoding Corruption

| Aspect | Details |
|--------|---------|
| **What triggers it** | Incorrect encoding detection; double-encoding; BOM issues; mixed encodings in single document |
| **How to detect it** | Replacement characters (); mojibake (Ã© instead of e); UnicodeDecodeError |
| **Handling strategy** | Use encoding detection cascade. Normalize to UTF-8. Strip BOM. Replace undecodable chars. |

```python
import codecs

def normalize_encoding(content_bytes):
    # Remove BOM if present
    if content_bytes.startswith(codecs.BOM_UTF8):
        content_bytes = content_bytes[3:]

    # Try encodings in order of likelihood
    encodings = ['utf-8', 'utf-8-sig', 'windows-1252', 'iso-8859-1', 'ascii']

    for encoding in encodings:
        try:
            text = content_bytes.decode(encoding)
            # Verify no replacement characters introduced
            if '\ufffd' not in text:
                return text
        except UnicodeDecodeError:
            continue

    # Last resort: lossy decode
    return content_bytes.decode('utf-8', errors='replace')
```

### 5.5 HTML Structure Changed

| Aspect | Details |
|--------|---------|
| **What triggers it** | Website redesign; A/B testing; localized versions; dynamic layouts |
| **How to detect it** | CSS selectors return None; expected elements missing; extraction returns wrong data |
| **Handling strategy** | Use multiple selector fallbacks. Implement content validation. Use generic extractors as backup. |

```python
from readability import Document  # python-readability

def extract_article_robust(html, url):
    """Multiple extraction strategies with fallbacks"""

    # Strategy 1: Site-specific selectors
    soup = BeautifulSoup(html, 'html.parser')

    # Try common article selectors
    selectors = [
        'article',
        '[role="main"]',
        '.post-content',
        '.article-body',
        '#content',
        'main',
    ]

    for selector in selectors:
        element = soup.select_one(selector)
        if element and len(element.get_text(strip=True)) > 200:
            return element.get_text(separator='\n', strip=True)

    # Strategy 2: Readability algorithm
    try:
        doc = Document(html)
        return doc.summary()
    except Exception as e:
        logger.debug(f"Readability extraction failed: {e}")

    # Strategy 3: Largest text block
    paragraphs = soup.find_all('p')
    if paragraphs:
        texts = [p.get_text(strip=True) for p in paragraphs]
        return '\n\n'.join(t for t in texts if len(t) > 50)

    raise ExtractionFailed(f"Could not extract content from {url}")
```

---

## 6. Output Failures

### 6.1 Markdown Generation Errors

| Aspect | Details |
|--------|---------|
| **What triggers it** | Special characters in content; unescaped brackets; malformed links; nested formatting issues |
| **How to detect it** | Markdown parser errors; broken rendering; raw markup visible |
| **Handling strategy** | Escape special characters. Validate markdown syntax. Use markdown library for generation. |

```python
import re

def escape_markdown(text):
    """Escape special markdown characters"""
    # Characters that need escaping in markdown
    special_chars = r'[\*\_\[\]\(\)\#\+\-\.\!\|\\`\{\}\~\>]'
    return re.sub(special_chars, r'\\\g<0>', text)

def safe_markdown_link(text, url):
    """Create a safe markdown link"""
    # Escape special chars in link text
    safe_text = text.replace('[', '\\[').replace(']', '\\]')
    # URL encode special chars in URL
    safe_url = url.replace('(', '%28').replace(')', '%29')
    return f"[{safe_text}]({safe_url})"

def validate_markdown(content):
    """Basic markdown validation"""
    issues = []

    # Check for unmatched brackets
    if content.count('[') != content.count(']'):
        issues.append("Unmatched square brackets")

    # Check for unmatched parentheses in links
    link_pattern = r'\[.*?\]\(.*?\)'
    links = re.findall(link_pattern, content)
    for link in links:
        if link.count('(') != link.count(')'):
            issues.append(f"Malformed link: {link}")

    return issues
```

### 6.2 Citation Formatting Issues

| Aspect | Details |
|--------|---------|
| **What triggers it** | Missing URL; URL contains special characters; title contains markdown syntax; duplicate citations |
| **How to detect it** | Broken citation links; citations not matching sources; markdown rendering errors |
| **Handling strategy** | Validate citations before including. Deduplicate. Generate unique citation keys. |

```python
from urllib.parse import urlparse, quote
from collections import OrderedDict

class CitationManager:
    def __init__(self):
        self.citations = OrderedDict()
        self.url_to_key = {}

    def add_citation(self, url, title=None):
        """Add citation and return reference key"""
        if not url:
            return None

        # Normalize URL
        url = url.strip()

        # Check for duplicate
        if url in self.url_to_key:
            return self.url_to_key[url]

        # Generate key
        key = len(self.citations) + 1

        # Clean title
        if title:
            title = title.strip()
            title = re.sub(r'\s+', ' ', title)  # Normalize whitespace
            title = title[:100]  # Limit length
        else:
            title = urlparse(url).netloc

        self.citations[key] = {'url': url, 'title': title}
        self.url_to_key[url] = key

        return key

    def format_reference(self, key):
        """Format inline reference"""
        return f"[{key}]"

    def generate_bibliography(self):
        """Generate markdown bibliography"""
        lines = ["\n## Sources\n"]

        for key, citation in self.citations.items():
            safe_url = quote(citation['url'], safe=':/?&=#')
            safe_title = escape_markdown(citation['title'])
            lines.append(f"[{key}]: {safe_url} \"{safe_title}\"")

        return '\n'.join(lines)
```

### 6.3 Report Structure Errors

| Aspect | Details |
|--------|---------|
| **What triggers it** | Missing sections; inconsistent heading levels; broken table of contents; template rendering failures |
| **How to detect it** | Structural validation; heading hierarchy check; TOC link validation |
| **Handling strategy** | Use templates with required sections. Validate structure before output. Auto-generate TOC from headings. |

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ReportSection:
    title: str
    level: int
    content: str
    subsections: List['ReportSection'] = field(default_factory=list)

class ReportBuilder:
    def __init__(self, title: str):
        self.title = title
        self.sections: List[ReportSection] = []
        self.current_level = 1

    def add_section(self, title: str, content: str, level: int = 2):
        if level < 1 or level > 6:
            raise ValueError(f"Invalid heading level: {level}")

        section = ReportSection(title=title, level=level, content=content)
        self.sections.append(section)
        return self

    def generate_toc(self):
        """Generate table of contents from sections"""
        toc_lines = ["## Table of Contents\n"]

        for i, section in enumerate(self.sections, 1):
            indent = "  " * (section.level - 2)
            anchor = section.title.lower().replace(' ', '-')
            anchor = re.sub(r'[^\w\-]', '', anchor)
            toc_lines.append(f"{indent}- [{section.title}](#{anchor})")

        return '\n'.join(toc_lines)

    def validate(self):
        """Validate report structure"""
        errors = []

        if not self.sections:
            errors.append("Report has no sections")

        # Check heading hierarchy
        prev_level = 1
        for section in self.sections:
            if section.level > prev_level + 1:
                errors.append(f"Heading level jump: {prev_level} -> {section.level}")
            prev_level = section.level

        return errors

    def build(self):
        """Build final markdown report"""
        errors = self.validate()
        if errors:
            logger.warning(f"Report validation issues: {errors}")

        parts = [f"# {self.title}\n"]
        parts.append(self.generate_toc())
        parts.append("")

        for section in self.sections:
            heading = "#" * section.level
            parts.append(f"{heading} {section.title}\n")
            parts.append(section.content)
            parts.append("")

        return '\n'.join(parts)
```

### 6.4 File Write Failures

| Aspect | Details |
|--------|---------|
| **What triggers it** | Permission denied; disk full; path doesn't exist; filename too long; invalid characters in filename |
| **How to detect it** | `PermissionError`, `OSError`, `FileNotFoundError` |
| **Handling strategy** | Validate path before writing. Create directories. Sanitize filenames. Handle atomic writes. |

```python
import os
import tempfile
import shutil

def sanitize_filename(filename):
    """Remove/replace invalid filename characters"""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    # Limit length (accounting for extension)
    max_length = 200
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length - len(ext)] + ext

    return filename

def safe_write_report(content, filepath):
    """Atomic write with error handling"""
    filepath = os.path.abspath(filepath)
    directory = os.path.dirname(filepath)

    # Ensure directory exists
    try:
        os.makedirs(directory, exist_ok=True)
    except PermissionError:
        raise OutputError(f"Cannot create directory: {directory}")

    # Write to temp file first, then move (atomic)
    try:
        fd, temp_path = tempfile.mkstemp(
            suffix='.md',
            dir=directory
        )

        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)

        # Atomic move
        shutil.move(temp_path, filepath)

    except PermissionError:
        raise OutputError(f"Permission denied: {filepath}")
    except OSError as e:
        if e.errno == 28:  # No space left on device
            raise OutputError("Disk full")
        raise OutputError(f"Write failed: {e}")
    finally:
        # Clean up temp file if it still exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
```

---

## Summary: Error Handling Best Practices

### Retry Strategy Decision Tree

```
Is the error transient?
├── YES (timeouts, rate limits, 5xx, DNS temporary)
│   └── Retry with exponential backoff
│       ├── Max 3-5 retries
│       ├── Initial delay: 1s
│       └── Max delay: 60s
│
└── NO (4xx client errors, invalid input, auth failures)
    └── Don't retry
        ├── Log the error
        ├── Return graceful fallback
        └── Alert if critical
```

### Universal Error Handler Pattern

```python
import logging
from functools import wraps
from typing import TypeVar, Callable
import time

T = TypeVar('T')

class RetryConfig:
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retryable_exceptions: tuple = (TimeoutError, ConnectionError),
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_exceptions = retryable_exceptions

def with_retry(config: RetryConfig = RetryConfig()):
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except config.retryable_exceptions as e:
                    last_exception = e

                    if attempt < config.max_retries:
                        delay = min(
                            config.initial_delay * (config.exponential_base ** attempt),
                            config.max_delay
                        )
                        logging.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}), "
                            f"retrying in {delay:.1f}s: {e}"
                        )
                        time.sleep(delay)
                    else:
                        logging.error(
                            f"{func.__name__} failed after {config.max_retries + 1} attempts"
                        )
                        raise

            raise last_exception

        return wrapper
    return decorator
```

### Logging Standards

```python
# Log levels for different failure modes
logging.DEBUG    # Transient failures that recovered
logging.INFO     # Rate limit waits, cache hits
logging.WARNING  # Retries, fallbacks used, truncation
logging.ERROR    # Permanent failures, skipped items
logging.CRITICAL # Authentication failures, quota exhausted
```

---

## References

### Documentation Sources
- [Anthropic Python SDK - Error Handling](https://github.com/anthropics/anthropic-sdk-python)
- [HTTPX Documentation - Exceptions](https://www.python-httpx.org/exceptions/)
- [Requests Documentation - Errors and Exceptions](https://requests.readthedocs.io/en/latest/user/quickstart/#errors-and-exceptions)

### Web Scraping Error Guides
- [ScraperAPI - Common Web Scraping Errors](https://www.scraperapi.com/blog/web-scraping-errors/)
- [Scrapfly - Bypass Cloudflare](https://scrapfly.io/blog/posts/how-to-bypass-cloudflare-anti-scraping)
- [ScrapeOps - Fix SSL Errors](https://scrapeops.io/python-web-scraping-playbook/python-requests-fix-ssl-error/)

### Encoding and Content Processing
- [WebScraping.AI - Encoding Issues with BeautifulSoup](https://webscraping.ai/faq/beautiful-soup/how-do-i-handle-encoding-issues-when-scraping-websites-with-beautiful-soup)
- [Forage.AI - Character Encoding Bugs Guide](https://forage.ai/blog/character-encoding-bugs-web-scraping-guide/)

### API Error Handling
- [SerpAPI Status and Error Codes](https://serpapi.com/api-status-and-error-codes)
- [Anthropic Claude Code Issues - Context Length](https://github.com/anthropics/claude-code/issues/5346)
- [Anthropic Claude Code Issues - Content Filtering](https://github.com/anthropics/claude-code/issues/6195)
