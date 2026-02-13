"""Custom exceptions and shared constants for the research agent."""

# Timeout for Anthropic API calls (seconds)
ANTHROPIC_TIMEOUT = 30.0


class ResearchError(Exception):
    """Base exception for research agent errors."""
    pass


class SearchError(ResearchError):
    """Raised when search fails."""
    pass


class SynthesisError(ResearchError):
    """Raised when report synthesis fails."""
    pass


class SkepticError(ResearchError):
    """Raised when skeptic review fails."""
    pass
