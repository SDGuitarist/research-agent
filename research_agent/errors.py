"""Custom exceptions for the research agent."""


class ResearchError(Exception):
    """Base exception for research agent errors."""
    pass


class SearchError(ResearchError):
    """Raised when search fails."""
    pass


class FetchError(ResearchError):
    """Raised when URL fetching fails."""
    pass


class ExtractionError(ResearchError):
    """Raised when content extraction fails."""
    pass


class SynthesisError(ResearchError):
    """Raised when report synthesis fails."""
    pass


class RelevanceError(ResearchError):
    """Raised when relevance scoring fails."""
    pass
