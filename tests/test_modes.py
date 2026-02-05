"""Tests for research_agent.modes module."""

import pytest
from research_agent.modes import ResearchMode


class TestResearchModeFactoryMethods:
    """Tests for ResearchMode factory methods."""

    def test_research_mode_quick_has_correct_parameters(self):
        """Quick mode should have 4 max sources (increased for relevance filtering), 2 passes, 300 word target."""
        mode = ResearchMode.quick()

        assert mode.name == "quick"
        assert mode.max_sources == 4  # Increased from 3 to account for relevance filtering
        assert mode.search_passes == 2
        assert mode.word_target == 300
        assert mode.max_tokens == 600
        assert mode.auto_save is False
        assert mode.pass1_sources == 4  # Increased from 2
        assert mode.pass2_sources == 2  # Increased from 1

    def test_research_mode_standard_has_correct_parameters(self):
        """Standard mode should have 10 max sources (increased for relevance filtering), 2 passes, 1000 word target."""
        mode = ResearchMode.standard()

        assert mode.name == "standard"
        assert mode.max_sources == 10  # Increased from 7 to account for relevance filtering
        assert mode.search_passes == 2
        assert mode.word_target == 1000
        assert mode.max_tokens == 1800
        assert mode.auto_save is True
        assert mode.pass1_sources == 6  # Increased from 4
        assert mode.pass2_sources == 4  # Increased from 3

    def test_research_mode_deep_has_correct_parameters(self):
        """Deep mode should have 12 max sources (increased for relevance filtering), 2 passes, 2000 word target."""
        mode = ResearchMode.deep()

        assert mode.name == "deep"
        assert mode.max_sources == 12  # Increased from 10 to account for relevance filtering
        assert mode.search_passes == 2
        assert mode.word_target == 2000
        assert mode.max_tokens == 3500
        assert mode.auto_save is True
        assert mode.pass1_sources == 12  # Increased from 10
        assert mode.pass2_sources == 12  # Increased from 10

    def test_research_mode_from_name_returns_quick(self):
        """from_name('quick') should return quick mode."""
        mode = ResearchMode.from_name("quick")

        assert mode.name == "quick"
        assert mode.max_sources == 4  # Increased from 3

    def test_research_mode_from_name_returns_standard(self):
        """from_name('standard') should return standard mode."""
        mode = ResearchMode.from_name("standard")

        assert mode.name == "standard"
        assert mode.max_sources == 10  # Increased from 7

    def test_research_mode_from_name_returns_deep(self):
        """from_name('deep') should return deep mode."""
        mode = ResearchMode.from_name("deep")

        assert mode.name == "deep"
        assert mode.max_sources == 12  # Increased from 10

    def test_research_mode_from_name_raises_on_unknown(self):
        """from_name() with unknown mode should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown mode: foo"):
            ResearchMode.from_name("foo")


class TestResearchModeValidation:
    """Tests for ResearchMode validation in __post_init__."""

    def test_research_mode_validation_rejects_zero_pass1_sources(self):
        """pass1_sources=0 should raise ValueError."""
        with pytest.raises(ValueError, match="pass1_sources must be >= 1"):
            ResearchMode(
                name="test",
                max_sources=5,
                search_passes=1,
                word_target=500,
                max_tokens=1000,
                auto_save=False,
                synthesis_instructions="Test",
                pass1_sources=0,
                pass2_sources=2,
                min_sources_full_report=3,
                min_sources_short_report=1,
            )

    def test_research_mode_validation_rejects_negative_pass2_sources(self):
        """pass2_sources=-1 should raise ValueError."""
        with pytest.raises(ValueError, match="pass2_sources must be >= 0"):
            ResearchMode(
                name="test",
                max_sources=5,
                search_passes=1,
                word_target=500,
                max_tokens=1000,
                auto_save=False,
                synthesis_instructions="Test",
                pass1_sources=3,
                pass2_sources=-1,
                min_sources_full_report=3,
                min_sources_short_report=1,
            )

    def test_research_mode_validation_rejects_empty_name(self):
        """Empty name should raise ValueError."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            ResearchMode(
                name="",
                max_sources=5,
                search_passes=1,
                word_target=500,
                max_tokens=1000,
                auto_save=False,
                synthesis_instructions="Test",
                pass1_sources=3,
                pass2_sources=2,
                min_sources_full_report=3,
                min_sources_short_report=1,
            )

    def test_research_mode_validation_rejects_max_sources_zero(self):
        """max_sources=0 should raise ValueError."""
        with pytest.raises(ValueError, match="max_sources must be >= 1"):
            ResearchMode(
                name="test",
                max_sources=0,
                search_passes=1,
                word_target=500,
                max_tokens=1000,
                auto_save=False,
                synthesis_instructions="Test",
                pass1_sources=3,
                pass2_sources=2,
                min_sources_full_report=3,
                min_sources_short_report=1,
            )

    def test_research_mode_validation_rejects_max_tokens_below_100(self):
        """max_tokens=99 should raise ValueError."""
        with pytest.raises(ValueError, match="max_tokens must be >= 100"):
            ResearchMode(
                name="test",
                max_sources=5,
                search_passes=1,
                word_target=500,
                max_tokens=99,
                auto_save=False,
                synthesis_instructions="Test",
                pass1_sources=3,
                pass2_sources=2,
                min_sources_full_report=3,
                min_sources_short_report=1,
            )

    def test_research_mode_validation_rejects_word_target_below_50(self):
        """word_target=49 should raise ValueError."""
        with pytest.raises(ValueError, match="word_target must be >= 50"):
            ResearchMode(
                name="test",
                max_sources=5,
                search_passes=1,
                word_target=49,
                max_tokens=1000,
                auto_save=False,
                synthesis_instructions="Test",
                pass1_sources=3,
                pass2_sources=2,
                min_sources_full_report=3,
                min_sources_short_report=1,
            )


class TestResearchModeBoundaryValues:
    """Tests for boundary values in ResearchMode validation."""

    def test_research_mode_validation_accepts_minimum_valid_config(self):
        """Minimum valid configuration should be accepted."""
        mode = ResearchMode(
            name="minimal",
            max_sources=1,
            search_passes=1,
            word_target=50,
            max_tokens=100,
            auto_save=False,
            synthesis_instructions="Minimal test",
            pass1_sources=1,
            pass2_sources=0,
            min_sources_full_report=1,
            min_sources_short_report=1,
        )

        assert mode.name == "minimal"
        assert mode.max_sources == 1
        assert mode.word_target == 50
        assert mode.max_tokens == 100
        assert mode.pass1_sources == 1
        assert mode.pass2_sources == 0
        assert mode.min_sources_full_report == 1
        assert mode.min_sources_short_report == 1

    def test_research_mode_is_frozen(self):
        """ResearchMode should be immutable (frozen dataclass)."""
        mode = ResearchMode.quick()

        with pytest.raises(AttributeError):
            mode.name = "modified"

    def test_research_mode_collects_multiple_validation_errors(self):
        """Multiple validation failures should all be reported."""
        with pytest.raises(ValueError) as exc_info:
            ResearchMode(
                name="",
                max_sources=0,
                search_passes=1,
                word_target=10,
                max_tokens=50,
                auto_save=False,
                synthesis_instructions="Test",
                pass1_sources=0,
                pass2_sources=-1,
                min_sources_full_report=3,
                min_sources_short_report=1,
            )

        error_message = str(exc_info.value)
        assert "name cannot be empty" in error_message
        assert "max_sources must be >= 1" in error_message
        assert "pass1_sources must be >= 1" in error_message
        assert "pass2_sources must be >= 0" in error_message


class TestResearchModeRelevanceThresholds:
    """Tests for relevance gate threshold validation."""

    def test_relevance_cutoff_must_be_between_1_and_5(self):
        """relevance_cutoff outside 1-5 range should raise ValueError."""
        with pytest.raises(ValueError, match="relevance_cutoff must be between 1 and 5"):
            ResearchMode(
                name="test",
                max_sources=5,
                search_passes=1,
                word_target=500,
                max_tokens=1000,
                auto_save=False,
                synthesis_instructions="Test",
                pass1_sources=3,
                pass2_sources=2,
                min_sources_full_report=3,
                min_sources_short_report=1,
                relevance_cutoff=6,
            )

    def test_relevance_cutoff_zero_is_invalid(self):
        """relevance_cutoff=0 should raise ValueError."""
        with pytest.raises(ValueError, match="relevance_cutoff must be between 1 and 5"):
            ResearchMode(
                name="test",
                max_sources=5,
                search_passes=1,
                word_target=500,
                max_tokens=1000,
                auto_save=False,
                synthesis_instructions="Test",
                pass1_sources=3,
                pass2_sources=2,
                min_sources_full_report=3,
                min_sources_short_report=1,
                relevance_cutoff=0,
            )

    def test_min_sources_short_report_must_be_at_least_1(self):
        """min_sources_short_report=0 should raise ValueError."""
        with pytest.raises(ValueError, match="min_sources_short_report must be >= 1"):
            ResearchMode(
                name="test",
                max_sources=5,
                search_passes=1,
                word_target=500,
                max_tokens=1000,
                auto_save=False,
                synthesis_instructions="Test",
                pass1_sources=3,
                pass2_sources=2,
                min_sources_full_report=3,
                min_sources_short_report=0,
            )

    def test_min_sources_short_report_must_not_exceed_full_report(self):
        """min_sources_short_report > min_sources_full_report should raise ValueError."""
        with pytest.raises(ValueError, match="min_sources_short_report.*must be <=.*min_sources_full_report"):
            ResearchMode(
                name="test",
                max_sources=5,
                search_passes=1,
                word_target=500,
                max_tokens=1000,
                auto_save=False,
                synthesis_instructions="Test",
                pass1_sources=3,
                pass2_sources=2,
                min_sources_full_report=2,
                min_sources_short_report=3,  # Greater than full_report threshold
            )

    def test_min_sources_full_report_must_not_exceed_max_sources(self):
        """min_sources_full_report > max_sources should raise ValueError."""
        with pytest.raises(ValueError, match="min_sources_full_report.*must be <=.*max_sources"):
            ResearchMode(
                name="test",
                max_sources=3,
                search_passes=1,
                word_target=500,
                max_tokens=1000,
                auto_save=False,
                synthesis_instructions="Test",
                pass1_sources=3,
                pass2_sources=2,
                min_sources_full_report=5,  # Greater than max_sources
                min_sources_short_report=1,
            )

    def test_quick_mode_has_correct_relevance_thresholds(self):
        """Quick mode should have correct relevance gate thresholds."""
        mode = ResearchMode.quick()
        assert mode.min_sources_full_report == 3
        assert mode.min_sources_short_report == 1
        assert mode.relevance_cutoff == 3

    def test_standard_mode_has_correct_relevance_thresholds(self):
        """Standard mode should have correct relevance gate thresholds."""
        mode = ResearchMode.standard()
        assert mode.min_sources_full_report == 4
        assert mode.min_sources_short_report == 2
        assert mode.relevance_cutoff == 3

    def test_deep_mode_has_correct_relevance_thresholds(self):
        """Deep mode should have correct relevance gate thresholds."""
        mode = ResearchMode.deep()
        assert mode.min_sources_full_report == 8  # Increased from 5 for more comprehensive deep reports
        assert mode.min_sources_short_report == 5  # Increased from 2
        assert mode.relevance_cutoff == 3
