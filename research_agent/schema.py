"""Gap data model for research schema."""

from dataclasses import dataclass, field
from enum import Enum


class GapStatus(Enum):
    """Status of a research gap."""

    UNKNOWN = "unknown"
    VERIFIED = "verified"
    STALE = "stale"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class Gap:
    """A single gap in the research schema.

    Represents one piece of intelligence that may need research.
    """

    id: str
    category: str
    status: GapStatus = GapStatus.UNKNOWN
    priority: int = 3
    last_verified: str | None = None
    last_checked: str | None = None
    ttl_days: int | None = None
    blocks: tuple[str, ...] = ()
    blocked_by: tuple[str, ...] = ()
    findings: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
