"""Tests for coverage gap parsing and dataclass."""

from research_agent.coverage import (
    CoverageGap,
    _parse_gap_response,
    _validate_retry_queries,
    _SAFE_DEFAULT,
    VALID_GAP_TYPES,
    VALID_RECOMMENDATIONS,
    MAX_RETRY_QUERIES,
)


# ── Happy path ────────────────────────────────────────────────────────

class TestParseGapResponseHappyPath:
    def test_well_formatted_query_mismatch(self):
        text = (
            "GAP_TYPE: QUERY_MISMATCH\n"
            "DESCRIPTION: Search used English but artist publishes in Spanish\n"
            "RETRY_RECOMMENDATION: RETRY\n"
            "REASONING: Query language doesn't match source language\n"
            "RETRY_QUERIES:\n"
            "- artista musical Mexico conciertos 2025\n"
            "- Latin indie music festival lineup\n"
            "- emerging artists Latin American scene\n"
        )
        result = _parse_gap_response(text)
        assert result.gap_type == "QUERY_MISMATCH"
        assert "English" in result.description
        assert result.retry_recommendation == "RETRY"
        assert len(result.retry_queries) == 3
        assert result.retry_queries[0] == "artista musical Mexico conciertos 2025"
        assert "language" in result.reasoning

    def test_coverage_gap_with_retry(self):
        text = (
            "GAP_TYPE: COVERAGE_GAP\n"
            "DESCRIPTION: Found general info but missing pricing data\n"
            "RETRY_RECOMMENDATION: RETRY\n"
            "REASONING: Specific subtopic not covered by initial results\n"
            "RETRY_QUERIES:\n"
            "- wedding venue pricing comparison data\n"
            "- average wedding cost breakdown 2025\n"
        )
        result = _parse_gap_response(text)
        assert result.gap_type == "COVERAGE_GAP"
        assert result.retry_recommendation == "RETRY"
        assert len(result.retry_queries) == 2

    def test_thin_footprint_maybe_retry(self):
        text = (
            "GAP_TYPE: THIN_FOOTPRINT\n"
            "DESCRIPTION: Artist has very limited online presence\n"
            "RETRY_RECOMMENDATION: MAYBE_RETRY\n"
            "REASONING: Subject is niche with few results\n"
            "RETRY_QUERIES:\n"
            "- Mike Hogan jazz performer venue schedule\n"
        )
        result = _parse_gap_response(text)
        assert result.gap_type == "THIN_FOOTPRINT"
        assert result.retry_recommendation == "MAYBE_RETRY"
        assert len(result.retry_queries) == 1

    def test_absence_no_retry(self):
        text = (
            "GAP_TYPE: ABSENCE\n"
            "DESCRIPTION: Information genuinely doesn't exist online\n"
            "RETRY_RECOMMENDATION: NO_RETRY\n"
            "REASONING: No evidence this data has ever been published\n"
            "RETRY_QUERIES:\n"
        )
        result = _parse_gap_response(text)
        assert result.gap_type == "ABSENCE"
        assert result.retry_recommendation == "NO_RETRY"
        assert result.retry_queries == ()

    def test_nonexistent_source(self):
        text = (
            "GAP_TYPE: NONEXISTENT_SOURCE\n"
            "DESCRIPTION: The specific report doesn't exist\n"
            "RETRY_RECOMMENDATION: NO_RETRY\n"
            "REASONING: User looking for a document that was never published\n"
            "RETRY_QUERIES:\n"
        )
        result = _parse_gap_response(text)
        assert result.gap_type == "NONEXISTENT_SOURCE"
        assert result.retry_recommendation == "NO_RETRY"


# ── NO_RETRY strips queries ──────────────────────────────────────────

class TestNoRetryStripsQueries:
    def test_no_retry_forces_empty_queries(self):
        """Even if Claude includes retry queries with NO_RETRY, they're stripped."""
        text = (
            "GAP_TYPE: ABSENCE\n"
            "DESCRIPTION: No data exists\n"
            "RETRY_RECOMMENDATION: NO_RETRY\n"
            "REASONING: Confirmed absence\n"
            "RETRY_QUERIES:\n"
            "- some retry query anyway\n"
            "- another one here\n"
        )
        result = _parse_gap_response(text)
        assert result.retry_recommendation == "NO_RETRY"
        assert result.retry_queries == ()

    def test_nonexistent_source_strips_queries(self):
        text = (
            "GAP_TYPE: NONEXISTENT_SOURCE\n"
            "DESCRIPTION: Report not found\n"
            "RETRY_RECOMMENDATION: NO_RETRY\n"
            "REASONING: Document never published\n"
            "RETRY_QUERIES:\n"
            "- alternative search query\n"
        )
        result = _parse_gap_response(text)
        assert result.retry_queries == ()


# ── Invalid gap type defaults ─────────────────────────────────────────

class TestInvalidGapType:
    def test_unknown_gap_type_defaults_to_coverage_gap(self):
        text = (
            "GAP_TYPE: SOMETHING_WEIRD\n"
            "DESCRIPTION: Unknown type\n"
            "RETRY_RECOMMENDATION: RETRY\n"
            "REASONING: Testing unknown type\n"
            "RETRY_QUERIES:\n"
            "- valid retry search query here\n"
        )
        result = _parse_gap_response(text)
        assert result.gap_type == "COVERAGE_GAP"

    def test_empty_gap_type_defaults(self):
        text = (
            "GAP_TYPE: \n"
            "DESCRIPTION: Empty type\n"
            "RETRY_RECOMMENDATION: NO_RETRY\n"
            "REASONING: Testing empty type\n"
        )
        result = _parse_gap_response(text)
        assert result.gap_type == "COVERAGE_GAP"

    def test_missing_gap_type_defaults(self):
        text = (
            "DESCRIPTION: No type field at all\n"
            "RETRY_RECOMMENDATION: NO_RETRY\n"
            "REASONING: Type line missing\n"
        )
        result = _parse_gap_response(text)
        assert result.gap_type == "COVERAGE_GAP"


# ── Invalid recommendation defaults ──────────────────────────────────

class TestInvalidRecommendation:
    def test_unknown_recommendation_defaults_to_no_retry(self):
        text = (
            "GAP_TYPE: COVERAGE_GAP\n"
            "DESCRIPTION: Bad recommendation\n"
            "RETRY_RECOMMENDATION: DEFINITELY_RETRY\n"
            "REASONING: Testing unknown rec\n"
            "RETRY_QUERIES:\n"
            "- some valid query here\n"
        )
        result = _parse_gap_response(text)
        assert result.retry_recommendation == "NO_RETRY"
        assert result.retry_queries == ()  # NO_RETRY forces empty

    def test_empty_recommendation_defaults(self):
        text = (
            "GAP_TYPE: QUERY_MISMATCH\n"
            "DESCRIPTION: Empty rec\n"
            "RETRY_RECOMMENDATION: \n"
            "REASONING: Testing empty\n"
        )
        result = _parse_gap_response(text)
        assert result.retry_recommendation == "NO_RETRY"

    def test_missing_recommendation_defaults(self):
        text = (
            "GAP_TYPE: QUERY_MISMATCH\n"
            "DESCRIPTION: No rec field\n"
            "REASONING: Rec line missing\n"
        )
        result = _parse_gap_response(text)
        assert result.retry_recommendation == "NO_RETRY"


# ── Empty / malformed response ────────────────────────────────────────

class TestMalformedResponse:
    def test_empty_string_returns_safe_default(self):
        result = _parse_gap_response("")
        assert result == _SAFE_DEFAULT

    def test_none_returns_safe_default(self):
        result = _parse_gap_response(None)
        assert result == _SAFE_DEFAULT

    def test_whitespace_only_returns_safe_default(self):
        result = _parse_gap_response("   \n  \n  ")
        assert result == _SAFE_DEFAULT

    def test_random_text_returns_graceful_default(self):
        result = _parse_gap_response("This is just random text with no structure")
        assert result.gap_type == "COVERAGE_GAP"
        assert result.retry_recommendation == "NO_RETRY"
        assert result.retry_queries == ()

    def test_partial_response_fills_defaults(self):
        text = "GAP_TYPE: QUERY_MISMATCH\n"
        result = _parse_gap_response(text)
        assert result.gap_type == "QUERY_MISMATCH"
        assert result.description == "Gap assessment returned no description"
        assert result.retry_recommendation == "NO_RETRY"
        assert result.retry_queries == ()


# ── Retry query validation ────────────────────────────────────────────

class TestRetryQueryValidation:
    def test_too_short_query_rejected(self):
        queries = ["hi"]
        valid = _validate_retry_queries(queries)
        assert valid == []

    def test_too_long_query_rejected(self):
        queries = ["this is a very long query with way too many words in it to be useful as a search"]
        valid = _validate_retry_queries(queries)
        assert valid == []

    def test_duplicate_queries_rejected(self):
        queries = [
            "wedding venue pricing comparison",
            "wedding venue pricing estimates",  # high overlap
        ]
        valid = _validate_retry_queries(queries)
        assert len(valid) == 1

    def test_similar_to_tried_queries_rejected(self):
        queries = ["luxury wedding market trends"]
        tried = ["luxury wedding market trends analysis"]
        valid = _validate_retry_queries(queries, tried_queries=tried)
        assert valid == []

    def test_max_queries_enforced(self):
        queries = [
            "unique search query alpha beta",
            "different search query gamma delta",
            "another search query epsilon zeta",
            "excess search query eta theta",
        ]
        valid = _validate_retry_queries(queries)
        assert len(valid) == MAX_RETRY_QUERIES

    def test_valid_queries_pass(self):
        queries = [
            "wedding venue pricing comparison data",
            "average catering cost breakdown 2025",
        ]
        valid = _validate_retry_queries(queries)
        assert len(valid) == 2

    def test_empty_list_returns_empty(self):
        valid = _validate_retry_queries([])
        assert valid == []

    def test_none_tried_queries_works(self):
        queries = ["valid search query here"]
        valid = _validate_retry_queries(queries, tried_queries=None)
        assert len(valid) == 1

    def test_queries_stripped_of_formatting(self):
        queries = ['"quoted search query here"']
        valid = _validate_retry_queries(queries)
        assert valid[0] == "quoted search query here"


# ── Parser with tried_queries ─────────────────────────────────────────

class TestParseWithTriedQueries:
    def test_tried_queries_filter_similar_retries(self):
        text = (
            "GAP_TYPE: QUERY_MISMATCH\n"
            "DESCRIPTION: Need different language\n"
            "RETRY_RECOMMENDATION: RETRY\n"
            "REASONING: Language mismatch\n"
            "RETRY_QUERIES:\n"
            "- luxury wedding market trends\n"  # too similar to tried
            "- artista musical Latin American scene\n"  # different enough
        )
        tried = ["luxury wedding market trends analysis"]
        result = _parse_gap_response(text, tried_queries=tried)
        assert len(result.retry_queries) == 1
        assert "artista" in result.retry_queries[0]

    def test_no_tried_queries_keeps_all_valid(self):
        text = (
            "GAP_TYPE: COVERAGE_GAP\n"
            "DESCRIPTION: Missing subtopic\n"
            "RETRY_RECOMMENDATION: RETRY\n"
            "REASONING: Subtopic gap\n"
            "RETRY_QUERIES:\n"
            "- wedding venue pricing comparison data\n"
            "- average catering cost breakdown 2025\n"
        )
        result = _parse_gap_response(text)
        assert len(result.retry_queries) == 2


# ── Case insensitivity ────────────────────────────────────────────────

class TestCaseInsensitivity:
    def test_lowercase_field_names_parsed(self):
        text = (
            "gap_type: QUERY_MISMATCH\n"
            "description: Lowercase field names\n"
            "retry_recommendation: RETRY\n"
            "reasoning: Testing case\n"
            "retry_queries:\n"
            "- valid search query here now\n"
        )
        result = _parse_gap_response(text)
        assert result.gap_type == "QUERY_MISMATCH"
        assert result.retry_recommendation == "RETRY"

    def test_lowercase_gap_type_value_uppercased(self):
        text = (
            "GAP_TYPE: query_mismatch\n"
            "DESCRIPTION: Lowercase value\n"
            "RETRY_RECOMMENDATION: retry\n"
            "REASONING: Testing value case\n"
            "RETRY_QUERIES:\n"
            "- valid search query here now\n"
        )
        result = _parse_gap_response(text)
        assert result.gap_type == "QUERY_MISMATCH"
        assert result.retry_recommendation == "RETRY"


# ── Constants ─────────────────────────────────────────────────────────

class TestConstants:
    def test_valid_gap_types_complete(self):
        expected = {"QUERY_MISMATCH", "THIN_FOOTPRINT", "ABSENCE",
                    "NONEXISTENT_SOURCE", "COVERAGE_GAP"}
        assert VALID_GAP_TYPES == expected

    def test_valid_recommendations_complete(self):
        expected = {"RETRY", "MAYBE_RETRY", "NO_RETRY"}
        assert VALID_RECOMMENDATIONS == expected

    def test_max_retry_queries_is_three(self):
        assert MAX_RETRY_QUERIES == 3


# ── CoverageGap dataclass ────────────────────────────────────────────

class TestCoverageGapDataclass:
    def test_frozen(self):
        gap = CoverageGap(
            gap_type="ABSENCE",
            description="Test",
            retry_recommendation="NO_RETRY",
            retry_queries=(),
            reasoning="Test",
        )
        try:
            gap.gap_type = "COVERAGE_GAP"
            assert False, "Should be frozen"
        except AttributeError:
            pass

    def test_safe_default_values(self):
        assert _SAFE_DEFAULT.gap_type == "COVERAGE_GAP"
        assert _SAFE_DEFAULT.retry_recommendation == "NO_RETRY"
        assert _SAFE_DEFAULT.retry_queries == ()
