"""Tests for research_agent.query_validation module."""

import pytest

from research_agent.query_validation import (
    meaningful_words,
    strip_query,
    has_near_duplicate,
    validate_query_list,
)


class TestMeaningfulWords:
    """Tests for meaningful_words() — word extraction with punctuation and hyphen handling."""

    def test_basic_extraction(self):
        assert meaningful_words("quantum computing research") == {
            "quantum", "computing", "research",
        }

    def test_excludes_stop_words(self):
        result = meaningful_words("the implications of quantum computing")
        assert "the" not in result
        assert "of" not in result
        assert "quantum" in result

    def test_strips_trailing_comma(self):
        result = meaningful_words("encryption standards, and protocols")
        assert "standards" in result
        assert "standards," not in result

    def test_strips_trailing_question_mark(self):
        result = meaningful_words("how are companies preparing?")
        assert "preparing" in result
        assert "preparing?" not in result

    def test_strips_various_punctuation(self):
        result = meaningful_words('test; value! "quoted" (parens) [brackets]')
        assert "test" in result
        assert "value" in result
        assert "quoted" in result
        assert "parens" in result
        assert "brackets" in result

    def test_hyphenated_word_kept_whole(self):
        result = meaningful_words("post-quantum cryptography")
        assert "post-quantum" in result

    def test_hyphenated_word_split_into_parts(self):
        result = meaningful_words("post-quantum cryptography")
        assert "post" in result
        assert "quantum" in result

    def test_hyphen_split_enables_overlap(self):
        """The core bug fix: 'post-quantum' should overlap with 'quantum'."""
        original = meaningful_words("quantum computing encryption")
        sub_query = meaningful_words("post-quantum cryptography threats")
        assert sub_query.intersection(original) == {"quantum"}

    def test_punctuation_enables_overlap(self):
        """The core bug fix: 'standards,' should overlap with 'standards'."""
        original = meaningful_words("encryption standards, and protocols")
        sub_query = meaningful_words("government regulations standards")
        assert "standards" in original.intersection(sub_query)

    def test_empty_string(self):
        assert meaningful_words("") == set()

    def test_only_stop_words(self):
        assert meaningful_words("the and or is") == set()

    def test_lowercase(self):
        result = meaningful_words("Quantum Computing")
        assert "quantum" in result
        assert "Quantum" not in result

    def test_are_is_stop_word(self):
        result = meaningful_words("how are governments preparing")
        assert "are" not in result

    def test_do_does_are_stop_words(self):
        result = meaningful_words("how do companies prepare and does it matter")
        assert "do" not in result
        assert "does" not in result


class TestValidateQueryListOverlap:
    """Tests for require_reference_overlap with punctuated references."""

    def test_punctuated_reference_matches_clean_sub_query(self):
        result = validate_query_list(
            ["government regulations standards"],
            min_words=2,
            max_words=10,
            max_results=3,
            reference_queries=["encryption standards, and protocols"],
            require_reference_overlap=True,
        )
        assert len(result) == 1

    def test_hyphenated_sub_query_matches_plain_reference(self):
        result = validate_query_list(
            ["post-quantum cryptography threats"],
            min_words=2,
            max_words=10,
            max_results=3,
            reference_queries=["quantum computing encryption"],
            require_reference_overlap=True,
        )
        assert len(result) == 1

    def test_no_overlap_still_rejected(self):
        result = validate_query_list(
            ["completely unrelated topic here"],
            min_words=2,
            max_words=10,
            max_results=3,
            reference_queries=["quantum computing encryption"],
            require_reference_overlap=True,
        )
        assert len(result) == 0
