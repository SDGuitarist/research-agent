"""Tests for CycleConfig dataclass."""

import dataclasses

import pytest

from research_agent.cycle_config import CycleConfig


class TestDefaultConfig:
    def test_default_config_valid(self):
        config = CycleConfig()
        assert config.max_gaps_per_run == 5
        assert config.max_tokens_per_prompt == 100_000
        assert config.reserved_output_tokens == 4096
        assert config.default_ttl_days == 30


class TestCustomConfig:
    def test_custom_config(self):
        config = CycleConfig(max_gaps_per_run=10)
        assert config.max_gaps_per_run == 10

    def test_all_custom_values(self):
        config = CycleConfig(
            max_gaps_per_run=3,
            max_tokens_per_prompt=50_000,
            reserved_output_tokens=2048,
            default_ttl_days=14,
        )
        assert config.max_gaps_per_run == 3
        assert config.max_tokens_per_prompt == 50_000
        assert config.reserved_output_tokens == 2048
        assert config.default_ttl_days == 14


class TestValidation:
    def test_invalid_gaps_per_run(self):
        with pytest.raises(ValueError, match="max_gaps_per_run must be >= 1"):
            CycleConfig(max_gaps_per_run=0)

    def test_invalid_tokens_per_prompt(self):
        with pytest.raises(ValueError, match="max_tokens_per_prompt must be >= 1000"):
            CycleConfig(max_tokens_per_prompt=500)

    def test_invalid_reserved_output_tokens(self):
        with pytest.raises(ValueError, match="reserved_output_tokens must be >= 256"):
            CycleConfig(reserved_output_tokens=100)

    def test_invalid_default_ttl_days(self):
        with pytest.raises(ValueError, match="default_ttl_days must be >= 1"):
            CycleConfig(default_ttl_days=0)

    def test_reserved_exceeds_max(self):
        with pytest.raises(ValueError, match="reserved_output_tokens.*must be <"):
            CycleConfig(
                max_tokens_per_prompt=5000,
                reserved_output_tokens=5000,
            )

    def test_reserved_greater_than_max(self):
        with pytest.raises(ValueError, match="reserved_output_tokens.*must be <"):
            CycleConfig(
                max_tokens_per_prompt=5000,
                reserved_output_tokens=6000,
            )

    def test_reports_all_errors(self):
        with pytest.raises(ValueError, match="Invalid CycleConfig:") as exc_info:
            CycleConfig(
                max_gaps_per_run=0,
                max_tokens_per_prompt=500,
                reserved_output_tokens=100,
                default_ttl_days=0,
            )
        message = str(exc_info.value)
        assert "max_gaps_per_run" in message
        assert "max_tokens_per_prompt" in message
        assert "reserved_output_tokens" in message
        assert "default_ttl_days" in message


class TestFrozen:
    def test_config_is_frozen(self):
        config = CycleConfig()
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.max_gaps_per_run = 10
