"""Tests for research_agent.context module."""

import pytest
from pathlib import Path
from unittest.mock import patch

from research_agent.context import (
    load_full_context,
    load_search_context,
    load_synthesis_context,
    _extract_sections,
)


SAMPLE_CONTEXT = """# Business Context

**Owner:** Test User

---

## Two Brands, One Operator

Brand info here.

## How the Brands Work Together

Synergy details here.

## Target Market

San Diego market info.

## Key Differentiators

Cultural authenticity details.

## Pricing Reference

Solo guitar $450-$650.

## Competitive Position

Primary competitor: Acoustic Spot Talent.

## What We Are NOT

Not a band. Not a DJ.

## Search & Research Parameters

Include: Solo guitarist, Spanish guitar.

## Research Matching Criteria

Strong fit: Luxury venue.

## Contact

alex@example.com
"""


class TestLoadFullContext:
    """Tests for load_full_context()."""

    def test_reads_file(self, tmp_path):
        """Should return full content when file exists."""
        ctx_file = tmp_path / "context.md"
        ctx_file.write_text("Full context content")
        result = load_full_context(ctx_file)
        assert result == "Full context content"

    def test_returns_none_missing_file(self, tmp_path):
        """Should return None when file does not exist."""
        result = load_full_context(tmp_path / "nonexistent.md")
        assert result is None

    def test_returns_none_empty_file(self, tmp_path):
        """Should return None when file is empty."""
        ctx_file = tmp_path / "context.md"
        ctx_file.write_text("")
        result = load_full_context(ctx_file)
        assert result is None

    def test_returns_none_whitespace_only(self, tmp_path):
        """Should return None when file has only whitespace."""
        ctx_file = tmp_path / "context.md"
        ctx_file.write_text("   \n\n  ")
        result = load_full_context(ctx_file)
        assert result is None


class TestExtractSections:
    """Tests for _extract_sections()."""

    def test_extracts_matching_sections(self):
        """Should include only matching sections."""
        result = _extract_sections(SAMPLE_CONTEXT, {"Target Market"})
        assert "Target Market" in result
        assert "San Diego market info" in result
        assert "Pricing Reference" not in result

    def test_preserves_header(self):
        """Should include content before first ## heading."""
        result = _extract_sections(SAMPLE_CONTEXT, {"Target Market"})
        assert "Business Context" in result
        assert "Owner" in result

    def test_empty_input(self):
        """Should return empty string for empty input."""
        result = _extract_sections("", {"Target Market"})
        assert result == ""

    def test_no_matching_sections(self):
        """Should return only the header when no sections match."""
        result = _extract_sections(SAMPLE_CONTEXT, {"Nonexistent Section"})
        # Should still have the header but no ## sections
        assert "Business Context" in result
        assert "Two Brands" not in result

    def test_case_insensitive_matching(self):
        """Section matching should be case-insensitive."""
        result = _extract_sections(SAMPLE_CONTEXT, {"target market"})
        assert "Target Market" in result
        assert "San Diego market info" in result

    def test_multiple_sections(self):
        """Should extract multiple matching sections."""
        result = _extract_sections(
            SAMPLE_CONTEXT, {"Target Market", "Key Differentiators"}
        )
        assert "Target Market" in result
        assert "Key Differentiators" in result
        assert "Pricing Reference" not in result


class TestLoadSearchContext:
    """Tests for load_search_context()."""

    def test_includes_search_sections(self, tmp_path):
        """Should include search-relevant sections."""
        ctx_file = tmp_path / "context.md"
        ctx_file.write_text(SAMPLE_CONTEXT)
        result = load_search_context(ctx_file)
        assert "Search & Research Parameters" in result
        assert "Target Market" in result
        assert "Two Brands, One Operator" in result
        assert "Research Matching Criteria" in result

    def test_excludes_pricing(self, tmp_path):
        """Should exclude Pricing Reference section."""
        ctx_file = tmp_path / "context.md"
        ctx_file.write_text(SAMPLE_CONTEXT)
        result = load_search_context(ctx_file)
        assert "Pricing Reference" not in result
        assert "$450" not in result

    def test_excludes_what_we_are_not(self, tmp_path):
        """Should exclude 'What We Are NOT' section."""
        ctx_file = tmp_path / "context.md"
        ctx_file.write_text(SAMPLE_CONTEXT)
        result = load_search_context(ctx_file)
        assert "What We Are NOT" not in result

    def test_returns_none_missing_file(self, tmp_path):
        """Should return None when context file is missing."""
        result = load_search_context(tmp_path / "nonexistent.md")
        assert result is None


class TestLoadSynthesisContext:
    """Tests for load_synthesis_context()."""

    def test_includes_competitive_position(self, tmp_path):
        """Should include Competitive Position section."""
        ctx_file = tmp_path / "context.md"
        ctx_file.write_text(SAMPLE_CONTEXT)
        result = load_synthesis_context(ctx_file)
        assert "Competitive Position" in result
        assert "Acoustic Spot Talent" in result

    def test_includes_key_differentiators(self, tmp_path):
        """Should include Key Differentiators section."""
        ctx_file = tmp_path / "context.md"
        ctx_file.write_text(SAMPLE_CONTEXT)
        result = load_synthesis_context(ctx_file)
        assert "Key Differentiators" in result

    def test_excludes_pricing(self, tmp_path):
        """Should exclude Pricing Reference section."""
        ctx_file = tmp_path / "context.md"
        ctx_file.write_text(SAMPLE_CONTEXT)
        result = load_synthesis_context(ctx_file)
        assert "Pricing Reference" not in result

    def test_excludes_contact(self, tmp_path):
        """Should exclude Contact section."""
        ctx_file = tmp_path / "context.md"
        ctx_file.write_text(SAMPLE_CONTEXT)
        result = load_synthesis_context(ctx_file)
        assert "alex@example.com" not in result

    def test_excludes_what_we_are_not(self, tmp_path):
        """Should exclude 'What We Are NOT' — causes defensive hedging."""
        ctx_file = tmp_path / "context.md"
        ctx_file.write_text(SAMPLE_CONTEXT)
        result = load_synthesis_context(ctx_file)
        assert "What We Are NOT" not in result
        assert "Not a band" not in result

    def test_returns_none_missing_file(self, tmp_path):
        """Should return None when context file is missing."""
        result = load_synthesis_context(tmp_path / "nonexistent.md")
        assert result is None
