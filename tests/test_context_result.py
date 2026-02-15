"""Tests for ContextResult type."""

import dataclasses

import pytest

from research_agent.context_result import ContextResult, ContextStatus


class TestContextStatus:
    """ContextStatus enum has exactly four values."""

    def test_exactly_four_values(self):
        assert len(ContextStatus) == 4
        assert set(ContextStatus) == {
            ContextStatus.LOADED,
            ContextStatus.NOT_CONFIGURED,
            ContextStatus.EMPTY,
            ContextStatus.FAILED,
        }


class TestContextResultTruthiness:
    """bool(result) reflects the four-state distinction."""

    def test_loaded_result_is_truthy(self):
        result = ContextResult.loaded("some text")
        assert bool(result) is True

    def test_not_configured_is_falsy(self):
        result = ContextResult.not_configured()
        assert bool(result) is False

    def test_empty_is_falsy(self):
        result = ContextResult.empty()
        assert bool(result) is False

    def test_failed_is_falsy(self):
        result = ContextResult.failed("timeout")
        assert bool(result) is False


class TestContextResultContent:
    """Factory methods set correct fields."""

    def test_loaded_carries_content(self):
        result = ContextResult.loaded("research data")
        assert result.content == "research data"
        assert result.status == ContextStatus.LOADED

    def test_failed_carries_error(self):
        result = ContextResult.failed("connection refused")
        assert result.error == "connection refused"
        assert result.status == ContextStatus.FAILED
        assert result.content is None

    def test_source_tracks_origin(self):
        result = ContextResult.loaded("data", source="/path/to/context.md")
        assert result.source == "/path/to/context.md"

    def test_source_tracks_origin_on_failed(self):
        result = ContextResult.failed("err", source="google_drive")
        assert result.source == "google_drive"

    def test_not_configured_has_no_content(self):
        result = ContextResult.not_configured()
        assert result.content is None
        assert result.status == ContextStatus.NOT_CONFIGURED

    def test_empty_has_no_content(self):
        result = ContextResult.empty(source="context.md")
        assert result.content is None
        assert result.status == ContextStatus.EMPTY
        assert result.source == "context.md"


class TestContextResultValidation:
    """Factory methods enforce correct field combinations."""

    def test_loaded_requires_content(self):
        with pytest.raises(ValueError, match="non-empty content"):
            ContextResult.loaded("")

    def test_failed_requires_error(self):
        with pytest.raises(ValueError, match="non-empty error"):
            ContextResult.failed("")

    def test_result_is_frozen(self):
        result = ContextResult.loaded("text")
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.content = "changed"  # type: ignore[misc]
