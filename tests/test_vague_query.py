"""Tests for vague query detection gate."""

import pytest

from research_agent.errors import ResearchError, VagueQueryError
from research_agent.query_validation import check_query_not_vague


class TestVagueQueryError:
    """VagueQueryError must be a ResearchError subclass for CLI/MCP error paths."""

    def test_is_research_error_subclass(self):
        assert issubclass(VagueQueryError, ResearchError)

    def test_caught_by_research_error_handler(self):
        with pytest.raises(ResearchError):
            raise VagueQueryError("test")


class TestCheckQueryNotVague:
    """Test corpus for the vague query gate (14 cases from plan)."""

    @pytest.mark.parametrize("query", [
        "stuff",
        "it",
        "a",
        "adidas",
        "2024",
        "   ",
    ])
    def test_rejects_vague_queries(self, query):
        with pytest.raises(VagueQueryError):
            check_query_not_vague(query)

    @pytest.mark.parametrize("query", [
        "Tesla",
        "NASA",
        "AI",
        "AI ethics",
        "climate change",
        "San Diego wedding venues",
        "what is AI",
        "what's up",  # "what's" survives stopword filter (only "what" is a stopword)
    ])
    def test_accepts_valid_queries(self, query):
        check_query_not_vague(query)  # should not raise

    def test_error_message_content(self):
        with pytest.raises(VagueQueryError, match="too vague for research"):
            check_query_not_vague("stuff")

    def test_proper_noun_with_punctuation(self):
        """Punctuation is stripped before the uppercase check."""
        check_query_not_vague('"Tesla"')  # quoted proper noun
        check_query_not_vague("NASA!")    # trailing punctuation

    def test_quoted_common_word_still_rejected(self):
        """Punctuation stripping doesn't save a common lowercase word."""
        with pytest.raises(VagueQueryError):
            check_query_not_vague("'stuff'")


class TestPythonAPIPath:
    """VagueQueryError propagates through the public Python API."""

    @pytest.mark.asyncio
    async def test_run_research_async_rejects_vague(self):
        from research_agent import run_research_async

        with pytest.raises(VagueQueryError):
            await run_research_async("stuff")
