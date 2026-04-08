"""Custom exceptions and shared constants for the research agent."""

from enum import StrEnum

from anthropic import APIError, RateLimitError, APIConnectionError, APITimeoutError

# Timeout for Anthropic API calls (seconds)
ANTHROPIC_TIMEOUT = 30.0

# Shared exception tuple for Anthropic API errors — use in except clauses
ANTHROPIC_ERRORS = (APIError, RateLimitError, APIConnectionError, APITimeoutError)


class GateDecision(StrEnum):
    """Gate decision for the relevance evaluation pipeline."""
    FULL_REPORT = "full_report"
    SHORT_REPORT = "short_report"
    INSUFFICIENT_DATA = "insufficient_data"
    NO_NEW_FINDINGS = "no_new_findings"


class ResearchError(Exception):
    """Base exception for research agent errors."""
    pass


class VagueQueryError(ResearchError):
    """Raised when query is too vague to produce useful research."""
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



class SchemaError(ResearchError):
    """YAML parse or validation failure.

    Carries a list of validation errors so callers see all problems at once.
    """

    def __init__(self, message: str = "", *, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors: list[str] = errors if errors is not None else []


class IterationError(ResearchError):
    """Raised when query iteration fails (API errors only).

    Validation rejections return empty results silently — they never raise.
    """
    pass


class StateError(ResearchError):
    """State file read/write/corruption failure."""
    pass


