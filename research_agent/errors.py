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


class ContextError(ResearchError):
    """Base exception for all context loading failures."""
    pass


class SchemaError(ResearchError):
    """YAML parse or validation failure.

    Carries a list of validation errors so callers see all problems at once.
    """

    def __init__(self, message: str = "", *, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors: list[str] = errors if errors is not None else []


class StateError(ResearchError):
    """State file read/write/corruption failure."""
    pass


class CritiqueError(ResearchError):
    """Raised when self-critique fails."""
    pass
