"""Typed result object for context loading operations.

Replaces str | None returns with a four-state result that distinguishes
loaded, not_configured, empty, and failed outcomes.
"""

from dataclasses import dataclass
from enum import Enum


class ContextStatus(Enum):
    LOADED = "loaded"
    NOT_CONFIGURED = "not_configured"
    EMPTY = "empty"
    FAILED = "failed"


@dataclass(frozen=True)
class ContextResult:
    """Result of a context loading operation.

    Use factory classmethods instead of constructing directly:
        ContextResult.loaded(content, source)
        ContextResult.not_configured(source)
        ContextResult.empty(source)
        ContextResult.failed(error, source)
    """

    content: str | None
    status: ContextStatus
    source: str = ""
    error: str = ""

    def __bool__(self) -> bool:
        """True only when content was successfully loaded."""
        return self.status == ContextStatus.LOADED and self.content is not None

    @classmethod
    def loaded(cls, content: str, source: str = "") -> "ContextResult":
        """Create a result for successfully loaded content.

        Raises:
            ValueError: If content is empty.
        """
        if not content:
            raise ValueError("loaded() requires non-empty content")
        return cls(content=content, status=ContextStatus.LOADED, source=source)

    @classmethod
    def not_configured(cls, source: str = "") -> "ContextResult":
        """Create a result indicating no context source is configured."""
        return cls(content=None, status=ContextStatus.NOT_CONFIGURED, source=source)

    @classmethod
    def empty(cls, source: str = "") -> "ContextResult":
        """Create a result indicating the source exists but has no content."""
        return cls(content=None, status=ContextStatus.EMPTY, source=source)

    @classmethod
    def failed(cls, error: str, source: str = "") -> "ContextResult":
        """Create a result for a failed loading attempt.

        Raises:
            ValueError: If error is empty.
        """
        if not error:
            raise ValueError("failed() requires a non-empty error string")
        return cls(content=None, status=ContextStatus.FAILED, source=source, error=error)
