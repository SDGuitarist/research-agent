"""Tests for research_agent.modes module."""

import pytest
from research_agent.modes import ResearchMode


class TestResearchModeFactoryMethods:
    """Tests for ResearchMode factory methods."""

    def test_research_mode_quick_has_correct_parameters(self):
        """Quick mode should have 3 sources, 2 passes, 300 word target."""
        mode = ResearchMode.quick()

        assert mode.name == "quick"
        assert mode.max_sources == 3
        assert mode.search_passes == 2
        assert mode.word_target == 300
        assert mode.max_tokens == 600
        assert mode.auto_save is False
        assert mode.pass1_sources == 2
        assert mode.pass2_sources == 1

    def test_research_mode_standard_has_correct_parameters(self):
        """Standard mode should have 7 sources, 2 passes, 1000 word target."""
        mode = ResearchMode.standard()

        assert mode.name == "standard"
        assert mode.max_sources == 7
        assert mode.search_passes == 2
        assert mode.word_target == 1000
        assert mode.max_tokens == 1800
        assert mode.auto_save is True
        assert mode.pass1_sources == 4
        assert mode.pass2_sources == 3

    def test_research_mode_deep_has_correct_parameters(self):
        """Deep mode should have 10 sources, 2 passes, 2000 word target."""
        mode = ResearchMode.deep()

        assert mode.name == "deep"
        assert mode.max_sources == 10
        assert mode.search_passes == 2
        assert mode.word_target == 2000
        assert mode.max_tokens == 3500
        assert mode.auto_save is True
        assert mode.pass1_sources == 10
        assert mode.pass2_sources == 10

    def test_research_mode_from_name_returns_quick(self):
        """from_name('quick') should return quick mode."""
        mode = ResearchMode.from_name("quick")

        assert mode.name == "quick"
        assert mode.max_sources == 3

    def test_research_mode_from_name_returns_standard(self):
        """from_name('standard') should return standard mode."""
        mode = ResearchMode.from_name("standard")

        assert mode.name == "standard"
        assert mode.max_sources == 7

    def test_research_mode_from_name_returns_deep(self):
        """from_name('deep') should return deep mode."""
        mode = ResearchMode.from_name("deep")

        assert mode.name == "deep"
        assert mode.max_sources == 10

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
        )

        assert mode.name == "minimal"
        assert mode.max_sources == 1
        assert mode.word_target == 50
        assert mode.max_tokens == 100
        assert mode.pass1_sources == 1
        assert mode.pass2_sources == 0

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
            )

        error_message = str(exc_info.value)
        assert "name cannot be empty" in error_message
        assert "max_sources must be >= 1" in error_message
        assert "pass1_sources must be >= 1" in error_message
        assert "pass2_sources must be >= 0" in error_message
