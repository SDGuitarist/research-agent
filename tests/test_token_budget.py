"""Tests for token budget utilities."""

from dataclasses import FrozenInstanceError
from unittest.mock import patch

import pytest

from research_agent.token_budget import (
    COMPONENT_PRIORITY,
    BudgetAllocation,
    allocate_budget,
    count_tokens,
)


# --- count_tokens tests ---


class TestCountTokens:
    def test_count_tokens_returns_int(self):
        """Returns positive int for non-empty string, 0 for empty."""
        result = count_tokens("Hello, this is a test string.")
        assert isinstance(result, int)
        assert result > 0

        assert count_tokens("") == 0

    def test_count_tokens_fallback(self):
        """With anthropic unavailable, falls back to char-based estimate."""
        import builtins

        real_import = builtins.__import__

        def fail_anthropic(name, *args, **kwargs):
            if name == "anthropic":
                raise ImportError("no anthropic")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fail_anthropic):
            result = count_tokens("a" * 400)
            assert isinstance(result, int)
            assert result == 100  # 400 / 4

    def test_count_tokens_fallback_on_api_error(self):
        """Falls back to char estimate when API call raises."""
        import anthropic as anthropic_mod

        with patch.object(
            anthropic_mod.Anthropic,
            "__init__",
            side_effect=RuntimeError("API error"),
        ):
            result = count_tokens("a" * 400)
            # Fallback: 400 chars / 4 = 100 tokens
            assert result == 100

    def test_count_tokens_fallback_minimum(self):
        """Fallback returns at least 1 for non-empty strings."""
        import anthropic as anthropic_mod

        with patch.object(
            anthropic_mod.Anthropic,
            "__init__",
            side_effect=RuntimeError("fail"),
        ):
            # 3 chars / 4 = 0, but should be at least 1
            result = count_tokens("abc")
            assert result >= 1


# --- BudgetAllocation tests ---


class TestBudgetAllocation:
    def test_budget_allocation_is_frozen(self):
        """BudgetAllocation is a frozen dataclass."""
        ba = BudgetAllocation(allocations={"a": 100}, pruned=[], total=100)
        with pytest.raises(FrozenInstanceError):
            ba.total = 999


# --- allocate_budget tests ---


class TestAllocateBudget:
    def _mock_count(self, text: str, model: str = "claude-sonnet-4-20250514") -> int:
        """Deterministic token counter: 1 token per 4 chars."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    def test_allocate_within_limit(self):
        """Sum of allocations <= max_tokens - reserved_output."""
        components = {
            "sources": "a" * 400,  # 100 tokens
            "instructions": "b" * 200,  # 50 tokens
        }
        with patch("research_agent.token_budget.count_tokens", side_effect=self._mock_count):
            result = allocate_budget(components, max_tokens=1000, reserved_output=100)
        assert result.total <= 1000 - 100

    def test_allocate_prunes_lowest_priority(self):
        """Staleness metadata pruned before sources."""
        components = {
            "staleness_metadata": "a" * 2000,  # 500 tokens, priority 1
            "sources": "b" * 2000,  # 500 tokens, priority 5
            "instructions": "c" * 400,  # 100 tokens, priority 6
        }
        with patch("research_agent.token_budget.count_tokens", side_effect=self._mock_count):
            result = allocate_budget(components, max_tokens=800, reserved_output=100)

        # staleness_metadata should be pruned before sources
        assert "staleness_metadata" in result.pruned
        # sources should NOT be pruned (or pruned after staleness_metadata)
        if "sources" in result.pruned:
            assert result.pruned.index("staleness_metadata") < result.pruned.index("sources")

    def test_allocate_preserves_instructions(self):
        """Instructions component is never pruned."""
        components = {
            "staleness_metadata": "a" * 2000,  # 500 tokens
            "instructions": "b" * 2000,  # 500 tokens, priority 6
        }
        with patch("research_agent.token_budget.count_tokens", side_effect=self._mock_count):
            result = allocate_budget(components, max_tokens=600, reserved_output=100)

        assert "instructions" not in result.pruned
        assert "instructions" in result.allocations
        assert result.allocations["instructions"] == 500  # Untouched

    def test_allocate_preserves_minimum(self):
        """Non-pruned components get at least 100 tokens."""
        components = {
            "staleness_metadata": "a" * 800,  # 200 tokens, priority 1
            "previous_baseline": "b" * 800,  # 200 tokens, priority 2
            "sources": "c" * 800,  # 200 tokens, priority 5
            "instructions": "d" * 400,  # 100 tokens, priority 6
        }
        with patch("research_agent.token_budget.count_tokens", side_effect=self._mock_count):
            # Available = 500 - 100 = 400 tokens for 700 total needed
            result = allocate_budget(components, max_tokens=500, reserved_output=100)

        for name, tokens in result.allocations.items():
            assert tokens >= 100, f"{name} has {tokens} tokens, expected >= 100"

    def test_allocate_reports_pruned(self):
        """`.pruned` contains names of truncated components."""
        components = {
            "staleness_metadata": "a" * 4000,  # 1000 tokens
            "sources": "b" * 4000,  # 1000 tokens
            "instructions": "c" * 400,  # 100 tokens
        }
        with patch("research_agent.token_budget.count_tokens", side_effect=self._mock_count):
            result = allocate_budget(components, max_tokens=1200, reserved_output=100)

        assert len(result.pruned) > 0
        # All pruned entries should be component names
        for name in result.pruned:
            assert name in components

    def test_allocate_under_budget_no_pruning(self):
        """When under budget, all components get full allocation."""
        components = {
            "staleness_metadata": "a" * 400,  # 100 tokens
            "sources": "b" * 400,  # 100 tokens
            "instructions": "c" * 400,  # 100 tokens
        }
        with patch("research_agent.token_budget.count_tokens", side_effect=self._mock_count):
            result = allocate_budget(components, max_tokens=10000, reserved_output=100)

        assert result.pruned == []
        assert result.total == 300
        assert result.allocations["staleness_metadata"] == 100
        assert result.allocations["sources"] == 100
        assert result.allocations["instructions"] == 100

    def test_allocate_empty_components(self):
        """Empty dict returns empty allocations."""
        result = allocate_budget({}, max_tokens=10000)
        assert result.allocations == {}
        assert result.pruned == []
        assert result.total == 0

    def test_allocate_single_oversized_component(self):
        """One component larger than budget gets truncated."""
        components = {
            "sources": "a" * 40000,  # 10000 tokens
        }
        with patch("research_agent.token_budget.count_tokens", side_effect=self._mock_count):
            result = allocate_budget(components, max_tokens=1000, reserved_output=100)

        # Should be truncated to fit within 900 available tokens
        assert result.total <= 900
        assert "sources" in result.pruned

    def test_allocate_custom_priorities(self):
        """Custom priorities override defaults."""
        components = {
            "custom_a": "a" * 2000,  # 500 tokens
            "custom_b": "b" * 2000,  # 500 tokens
        }
        custom_prio = {"custom_a": 10, "custom_b": 1}  # b pruned first
        with patch("research_agent.token_budget.count_tokens", side_effect=self._mock_count):
            result = allocate_budget(
                components,
                max_tokens=800,
                reserved_output=100,
                priorities=custom_prio,
            )

        assert "custom_b" in result.pruned
        # custom_a should be intact or at least not pruned before custom_b
        if "custom_a" in result.pruned:
            assert result.pruned.index("custom_b") < result.pruned.index("custom_a")


class TestComponentPriority:
    def test_priority_ordering(self):
        """Staleness has lowest priority, instructions has highest."""
        assert COMPONENT_PRIORITY["staleness_metadata"] < COMPONENT_PRIORITY["sources"]
        assert COMPONENT_PRIORITY["sources"] < COMPONENT_PRIORITY["instructions"]
        assert COMPONENT_PRIORITY["instructions"] == 6
