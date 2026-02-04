# Test Suite Plan for Research Agent

## Overview

This document outlines a comprehensive pytest-based test suite for the research agent. The tests are designed to be:
- **Fast**: All external calls mocked
- **Free**: No real API calls
- **Reliable**: No network dependency
- **Focused**: Each test verifies ONE thing with a descriptive name

## Test Infrastructure

### Dependencies to Add

```
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

No additional mocking library needed — we use `unittest.mock` from the Python standard library.

### Directory Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures
├── test_fetch.py                  # URL fetching tests
├── test_search.py                 # Search and query refinement tests
├── test_summarize.py              # Content summarization tests
├── test_synthesize.py             # Report synthesis tests
├── test_modes.py                  # Research mode validation tests
├── test_extract.py                # Content extraction tests
├── test_agent.py                  # Integration tests for ResearchAgent
└── fixtures/                      # Test data files
    ├── sample_html_simple.html
    ├── sample_html_complex.html
    └── sample_html_empty.html
```

### conftest.py Fixtures

| Fixture | Purpose |
|---------|---------|
| `sample_html_simple` | Basic HTML page with article content |
| `sample_html_complex` | Page with navigation, footer, ads to test extraction |
| `sample_html_empty` | Page with only boilerplate (nav, footer) |
| `sample_html_oversized` | HTML exceeding 5MB limit |
| `mock_anthropic_client` | Mocked sync Anthropic client |
| `mock_async_anthropic_client` | Mocked async Anthropic client |
| `mock_ddgs` | Mocked DuckDuckGo search context manager |
| `mock_httpx_client` | Mocked httpx.AsyncClient |
| `sample_search_results` | List of SearchResult objects |
| `sample_summaries` | List of Summary objects |
| `sample_fetched_pages` | List of FetchedPage objects |
| `sample_extracted_content` | List of ExtractedContent objects |

---

## Test Files Detail

### 1. test_fetch.py — URL Fetching Tests (19 tests)

#### Unit Tests: `_is_private_ip()` (7 tests)

| Test Name | Description |
|-----------|-------------|
| `test_is_private_ip_returns_true_for_loopback_127_0_0_1` | 127.0.0.1 is private |
| `test_is_private_ip_returns_true_for_loopback_ipv6` | ::1 is private |
| `test_is_private_ip_returns_true_for_10_x_range` | 10.0.0.1 is private |
| `test_is_private_ip_returns_true_for_172_16_range` | 172.16.0.1 is private |
| `test_is_private_ip_returns_true_for_192_168_range` | 192.168.1.1 is private |
| `test_is_private_ip_returns_true_for_link_local` | 169.254.169.254 (AWS metadata) is private |
| `test_is_private_ip_returns_false_for_public_ip` | 8.8.8.8 is not private |

#### Unit Tests: `_is_safe_url()` (8 tests)

| Test Name | Description |
|-----------|-------------|
| `test_is_safe_url_allows_https_public_url` | https://example.com is safe |
| `test_is_safe_url_allows_http_public_url` | http://example.com is safe |
| `test_is_safe_url_blocks_file_scheme` | file:///etc/passwd is unsafe |
| `test_is_safe_url_blocks_ftp_scheme` | ftp://example.com is unsafe |
| `test_is_safe_url_blocks_localhost` | http://localhost is unsafe |
| `test_is_safe_url_blocks_127_0_0_1` | http://127.0.0.1 is unsafe |
| `test_is_safe_url_blocks_private_ip_ranges` | http://10.0.0.1 is unsafe |
| `test_is_safe_url_returns_false_for_empty_url` | Empty string is unsafe |

#### Unit Tests with Mocking: `fetch_urls()` (4 tests)

| Test Name | Description |
|-----------|-------------|
| `test_fetch_urls_returns_fetched_pages_on_success` | Mock httpx, verify FetchedPage returned |
| `test_fetch_urls_skips_403_forbidden_responses` | 403 returns None, not in results |
| `test_fetch_urls_skips_timeout_errors` | TimeoutException returns None |
| `test_fetch_urls_filters_non_html_content_types` | application/pdf skipped |

---

### 2. test_search.py — Search Tests (14 tests)

#### Unit Tests: `_sanitize_for_prompt()` (4 tests)

| Test Name | Description |
|-----------|-------------|
| `test_sanitize_for_prompt_escapes_angle_brackets` | `<script>` becomes `&lt;script&gt;` |
| `test_sanitize_for_prompt_handles_empty_string` | Empty string returns empty |
| `test_sanitize_for_prompt_preserves_normal_text` | Text without special chars unchanged |
| `test_sanitize_for_prompt_escapes_nested_tags` | `</system>` escaped properly |

#### Unit Tests with Mocking: `search()` (5 tests)

| Test Name | Description |
|-----------|-------------|
| `test_search_returns_results_on_success` | Mock DDGS, verify SearchResult list |
| `test_search_raises_error_on_empty_results` | Empty results raise SearchError |
| `test_search_retries_on_rate_limit` | RatelimitException triggers retry |
| `test_search_respects_max_results` | max_results parameter honored |
| `test_search_filters_results_without_url` | Results missing href excluded |

#### Unit Tests with Mocking: `refine_query()` (5 tests)

| Test Name | Description |
|-----------|-------------|
| `test_refine_query_returns_refined_query_on_success` | Mock Anthropic, verify refined query |
| `test_refine_query_returns_original_on_api_error` | APIError falls back to original |
| `test_refine_query_returns_original_on_rate_limit` | RateLimitError falls back to original |
| `test_refine_query_returns_original_on_empty_response` | Empty content falls back to original |
| `test_refine_query_sanitizes_summaries` | Summaries with `<>` are escaped |

---

### 3. test_summarize.py — Summarization Tests (13 tests)

#### Unit Tests: `_sanitize_content()` (3 tests)

| Test Name | Description |
|-----------|-------------|
| `test_sanitize_content_escapes_angle_brackets` | `<script>` becomes `&lt;script&gt;` |
| `test_sanitize_content_handles_empty_string` | Empty string returns empty |
| `test_sanitize_content_handles_multiple_tags` | Multiple `<>` pairs all escaped |

#### Unit Tests: `_chunk_text()` (5 tests)

| Test Name | Description |
|-----------|-------------|
| `test_chunk_text_returns_single_chunk_for_short_text` | Text under chunk size returns as-is |
| `test_chunk_text_splits_at_paragraph_boundaries` | Prefers `\n\n` break points |
| `test_chunk_text_splits_at_newlines_when_no_paragraphs` | Falls back to `\n` |
| `test_chunk_text_limits_to_max_chunks` | MAX_CHUNKS_PER_SOURCE honored |
| `test_chunk_text_handles_empty_string` | Empty string returns empty list |

#### Unit Tests with Mocking: `summarize_chunk()` (5 tests)

| Test Name | Description |
|-----------|-------------|
| `test_summarize_chunk_returns_summary_on_success` | Mock AsyncAnthropic, verify Summary |
| `test_summarize_chunk_returns_none_on_api_error` | APIError returns None |
| `test_summarize_chunk_propagates_rate_limit_error` | RateLimitError re-raised |
| `test_summarize_chunk_sanitizes_content` | Content with `<>` escaped in prompt |
| `test_summarize_chunk_returns_none_on_malformed_response` | Missing content[0] returns None |

---

### 4. test_synthesize.py — Synthesis Tests (12 tests)

#### Unit Tests: `_sanitize_content()` (2 tests)

| Test Name | Description |
|-----------|-------------|
| `test_sanitize_content_escapes_angle_brackets` | Same escaping as summarize |
| `test_sanitize_content_handles_empty_string` | Empty string returns empty |

#### Unit Tests: `_deduplicate_summaries()` (5 tests)

| Test Name | Description |
|-----------|-------------|
| `test_deduplicate_summaries_removes_exact_duplicates` | Identical strings deduplicated |
| `test_deduplicate_summaries_normalizes_whitespace` | "a  b" matches "a b" |
| `test_deduplicate_summaries_preserves_order` | First occurrence kept |
| `test_deduplicate_summaries_handles_empty_list` | Empty list returns empty |
| `test_deduplicate_summaries_keeps_unique_summaries` | Distinct summaries preserved |

#### Unit Tests with Mocking: `synthesize_report()` (5 tests)

| Test Name | Description |
|-----------|-------------|
| `test_synthesize_report_returns_markdown_on_success` | Mock streaming, verify report |
| `test_synthesize_report_raises_on_empty_summaries` | Empty list raises SynthesisError |
| `test_synthesize_report_raises_on_rate_limit` | RateLimitError wrapped in SynthesisError |
| `test_synthesize_report_raises_on_timeout` | APITimeoutError wrapped in SynthesisError |
| `test_synthesize_report_raises_on_empty_response` | Empty stream raises SynthesisError |

---

### 5. test_modes.py — Research Mode Tests (14 tests)

#### Unit Tests: ResearchMode Validation (10 tests)

| Test Name | Description |
|-----------|-------------|
| `test_research_mode_quick_has_correct_parameters` | Verify quick mode defaults |
| `test_research_mode_standard_has_correct_parameters` | Verify standard mode defaults |
| `test_research_mode_deep_has_correct_parameters` | Verify deep mode defaults |
| `test_research_mode_from_name_returns_quick` | from_name("quick") works |
| `test_research_mode_from_name_returns_standard` | from_name("standard") works |
| `test_research_mode_from_name_returns_deep` | from_name("deep") works |
| `test_research_mode_from_name_raises_on_unknown` | from_name("foo") raises ValueError |
| `test_research_mode_validation_rejects_zero_pass1_sources` | pass1_sources=0 raises |
| `test_research_mode_validation_rejects_negative_pass2_sources` | pass2_sources=-1 raises |
| `test_research_mode_validation_rejects_empty_name` | name="" raises |

#### Boundary Value Tests (4 tests)

| Test Name | Description |
|-----------|-------------|
| `test_research_mode_validation_accepts_minimum_valid_config` | Minimum valid values accepted |
| `test_research_mode_validation_rejects_max_sources_zero` | max_sources=0 raises |
| `test_research_mode_validation_rejects_max_tokens_below_100` | max_tokens=99 raises |
| `test_research_mode_validation_rejects_word_target_below_50` | word_target=49 raises |

---

### 6. test_extract.py — Content Extraction Tests (10 tests)

#### Unit Tests: `extract_content()` (10 tests)

| Test Name | Description |
|-----------|-------------|
| `test_extract_content_extracts_from_simple_html` | Basic article extracted |
| `test_extract_content_extracts_title` | Title tag captured |
| `test_extract_content_returns_none_for_oversized_html` | >5MB returns None |
| `test_extract_content_returns_none_for_empty_page` | Only nav/footer returns None |
| `test_extract_content_returns_none_for_short_content` | <100 chars returns None |
| `test_extract_content_uses_readability_fallback` | Trafilatura fails, readability works |
| `test_extract_content_handles_malformed_html` | Parser doesn't crash on bad HTML |
| `test_extract_all_returns_list_of_extracted_content` | Multiple pages processed |
| `test_extract_all_skips_failed_extractions` | Failed extractions not in list |
| `test_extract_content_handles_unicode_content` | UTF-8 content preserved |

---

### 7. test_agent.py — Integration Tests (12 tests)

#### Integration Tests: Quick Mode Pipeline (4 tests)

| Test Name | Description |
|-----------|-------------|
| `test_research_quick_mode_completes_pipeline` | Mock all externals, verify report generated |
| `test_research_quick_mode_uses_correct_source_count` | Verifies pass1=2, pass2=1 sources |
| `test_research_quick_mode_deduplicates_urls` | Same URL from both passes appears once |
| `test_research_quick_mode_continues_on_pass2_failure` | Pass 2 SearchError non-fatal |

#### Integration Tests: Standard Mode Pipeline (3 tests)

| Test Name | Description |
|-----------|-------------|
| `test_research_standard_mode_completes_pipeline` | Full pipeline with pass1=4, pass2=3 |
| `test_research_standard_mode_refines_query_from_snippets` | refine_query() called with snippets |
| `test_research_standard_mode_auto_saves_enabled` | mode.auto_save is True |

#### Integration Tests: Deep Mode Pipeline (3 tests)

| Test Name | Description |
|-----------|-------------|
| `test_research_deep_mode_completes_pipeline` | Full pipeline with fetch between passes |
| `test_research_deep_mode_refines_query_from_summaries` | refine_query() called with summaries |
| `test_research_deep_mode_fetches_new_urls_in_pass2` | Second fetch_urls() call made |

#### Integration Tests: Error Handling (2 tests)

| Test Name | Description |
|-----------|-------------|
| `test_research_raises_error_when_search_fails` | Pass 1 failure raises ResearchError |
| `test_research_raises_error_when_no_pages_fetched` | Empty fetch raises ResearchError |

---

## Test Count Summary

| Test File | Test Count |
|-----------|------------|
| test_fetch.py | 19 |
| test_search.py | 14 |
| test_summarize.py | 13 |
| test_synthesize.py | 12 |
| test_modes.py | 14 |
| test_extract.py | 10 |
| test_agent.py | 12 |
| **Total** | **94** |

---

## Implementation Notes

### Async Test Pattern

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_fetch_urls_returns_fetched_pages_on_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>Content</body></html>"
    mock_response.headers = {"content-type": "text/html"}
    mock_response.url = "https://example.com"

    with patch("research_agent.fetch.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        results = await fetch_urls(["https://example.com"])

        assert len(results) == 1
        assert results[0].url == "https://example.com"
```

### Mocking Anthropic Streaming

```python
from unittest.mock import MagicMock, patch

def test_synthesize_report_returns_markdown_on_success(sample_summaries):
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_stream.text_stream = iter(["# Report", "\n", "Content here"])

    with patch("research_agent.synthesize.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream

        report = synthesize_report(
            client=mock_client,
            query="test query",
            summaries=sample_summaries,
        )

        assert "# Report" in report
```

### Mocking DuckDuckGo Search

```python
from unittest.mock import MagicMock, patch

def test_search_returns_results_on_success():
    mock_results = [
        {"title": "Result 1", "href": "https://example1.com", "body": "Snippet 1"},
        {"title": "Result 2", "href": "https://example2.com", "body": "Snippet 2"},
    ]

    with patch("research_agent.search.DDGS") as mock_ddgs:
        mock_instance = MagicMock()
        mock_instance.text.return_value = mock_results
        mock_ddgs.return_value.__enter__.return_value = mock_instance

        results = search("test query", max_results=5)

        assert len(results) == 2
        assert results[0].title == "Result 1"
```

---

## Fixture Examples

### conftest.py

```python
import pytest
from research_agent.fetch import FetchedPage
from research_agent.extract import ExtractedContent
from research_agent.summarize import Summary
from research_agent.search import SearchResult

@pytest.fixture
def sample_html_simple():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Article</title></head>
    <body>
        <article>
            <h1>Test Article Title</h1>
            <p>This is the first paragraph with enough content to pass the
            minimum length threshold. It contains useful information about
            the topic being researched.</p>
            <p>This is the second paragraph with additional details and
            supporting information for the research query.</p>
        </article>
    </body>
    </html>
    """

@pytest.fixture
def sample_html_oversized():
    # Generate HTML larger than 5MB
    return "<html><body>" + "x" * (6 * 1024 * 1024) + "</body></html>"

@pytest.fixture
def sample_search_results():
    return [
        SearchResult(
            title="Result 1",
            url="https://example1.com/article",
            snippet="First result snippet with information."
        ),
        SearchResult(
            title="Result 2",
            url="https://example2.com/page",
            snippet="Second result snippet with different info."
        ),
    ]

@pytest.fixture
def sample_summaries():
    return [
        Summary(
            url="https://example1.com",
            title="Article 1",
            summary="Summary of the first article with key findings."
        ),
        Summary(
            url="https://example2.com",
            title="Article 2",
            summary="Summary of the second article with different points."
        ),
    ]

@pytest.fixture
def sample_fetched_pages(sample_html_simple):
    return [
        FetchedPage(
            url="https://example1.com",
            html=sample_html_simple,
            status_code=200
        ),
    ]

@pytest.fixture
def sample_extracted_content():
    return [
        ExtractedContent(
            url="https://example1.com",
            title="Test Article",
            text="This is extracted content with enough length to be processed."
        ),
    ]
```

---

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_fetch.py

# Run specific test
pytest tests/test_fetch.py::test_is_safe_url_blocks_localhost

# Run with coverage
pytest tests/ --cov=research_agent --cov-report=html

# Run only async tests
pytest tests/ -m asyncio
```

### pytest.ini Configuration

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
```

---

## Key Design Decisions

### 1. No Real Network Calls
Every external service is mocked:
- DuckDuckGo via `patch("research_agent.search.DDGS")`
- Anthropic via `patch("research_agent.summarize.AsyncAnthropic")`
- HTTP via `patch("research_agent.fetch.httpx.AsyncClient")`

### 2. Descriptive Test Names
Each test name follows the pattern:
```
test_{function_name}_{expected_behavior}_{condition}
```

Examples:
- `test_is_safe_url_blocks_private_ip_ranges`
- `test_refine_query_returns_original_on_api_error`
- `test_research_quick_mode_continues_on_pass2_failure`

### 3. One Assertion Per Test (Mostly)
Each test verifies ONE behavior. Multiple assertions only when testing related properties of a single operation.

### 4. Fixtures Over Setup
Reusable test data defined as fixtures in `conftest.py` rather than duplicated in each test file.

### 5. Integration Tests Mock at Boundaries
Integration tests mock external services but exercise real internal code paths, verifying the full pipeline works together.

---

## Files to Create

1. `tests/__init__.py` — Empty, marks as package
2. `tests/conftest.py` — Shared fixtures
3. `tests/test_fetch.py` — 19 tests
4. `tests/test_search.py` — 14 tests
5. `tests/test_summarize.py` — 13 tests
6. `tests/test_synthesize.py` — 12 tests
7. `tests/test_modes.py` — 14 tests
8. `tests/test_extract.py` — 10 tests
9. `tests/test_agent.py` — 12 tests
10. `tests/fixtures/sample_html_simple.html` — Test HTML
11. `tests/fixtures/sample_html_complex.html` — Test HTML with noise
12. `tests/fixtures/sample_html_empty.html` — Empty content page

---

## Next Steps

1. Create `tests/` directory structure
2. Add pytest dependencies to requirements.txt
3. Create `conftest.py` with all fixtures
4. Implement test files in order:
   - test_modes.py (simplest, no mocking needed for most)
   - test_fetch.py (unit tests first, then mocked)
   - test_search.py
   - test_summarize.py
   - test_synthesize.py
   - test_extract.py
   - test_agent.py (integration tests last)
5. Run tests and verify all pass
6. Add CI configuration (GitHub Actions)
