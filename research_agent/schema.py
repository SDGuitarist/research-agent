"""Gap data model and YAML parser for research schema."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import yaml

from .errors import SchemaError


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


@dataclass(frozen=True)
class SchemaResult:
    """Result of loading a gap schema file.

    Follows the three-way pattern from ContextResult:
    - gaps is non-empty and is_loaded is True: schema loaded successfully
    - gaps is empty and is_empty is True: file exists but has no gaps
    - gaps is empty and is_not_configured is True: file does not exist
    """

    gaps: tuple[Gap, ...]
    source: str = ""

    @property
    def is_loaded(self) -> bool:
        return len(self.gaps) > 0

    @property
    def is_empty(self) -> bool:
        return len(self.gaps) == 0 and self.source != ""

    @property
    def is_not_configured(self) -> bool:
        return len(self.gaps) == 0 and self.source == ""

    def __bool__(self) -> bool:
        return self.is_loaded


# Valid GapStatus values for YAML parsing
_VALID_STATUSES = {s.value for s in GapStatus}


def _parse_gap(raw: dict, index: int) -> Gap:
    """Parse a single gap dict from YAML into a Gap object.

    Raises SchemaError for missing required fields or invalid values.
    """
    if "id" not in raw:
        raise SchemaError(f"Gap at index {index} is missing required field 'id'")
    if "category" not in raw:
        raise SchemaError(f"Gap at index {index} is missing required field 'category'")

    status_str = raw.get("status", "unknown")
    if status_str not in _VALID_STATUSES:
        raise SchemaError(
            f"Gap '{raw['id']}' has unknown status '{status_str}'. "
            f"Valid values: {sorted(_VALID_STATUSES)}"
        )

    blocks = raw.get("blocks", ())
    blocked_by = raw.get("blocked_by", ())

    return Gap(
        id=raw["id"],
        category=raw["category"],
        status=GapStatus(status_str),
        priority=raw.get("priority", 3),
        last_verified=raw.get("last_verified"),
        last_checked=raw.get("last_checked"),
        ttl_days=raw.get("ttl_days"),
        blocks=tuple(blocks) if blocks else (),
        blocked_by=tuple(blocked_by) if blocked_by else (),
        findings=raw.get("findings", ""),
        metadata=raw.get("metadata", {}),
    )


def load_schema(path: Path | str) -> SchemaResult:
    """Load a gap schema from a YAML file.

    Args:
        path: Path to the YAML schema file.

    Returns:
        SchemaResult with parsed Gap objects.

    Raises:
        SchemaError: If the file exists but contains invalid YAML or
            the YAML structure doesn't match the expected schema format.
    """
    path = Path(path)

    if not path.exists():
        return SchemaResult(gaps=())

    source = str(path)
    text = path.read_text()

    if not text.strip():
        return SchemaResult(gaps=(), source=source)

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise SchemaError(f"Invalid YAML in {source}: {exc}") from exc

    if data is None:
        return SchemaResult(gaps=(), source=source)

    if not isinstance(data, dict) or "gaps" not in data:
        raise SchemaError(f"Schema in {source} must have a top-level 'gaps' key")

    raw_gaps = data["gaps"]

    if raw_gaps is None or (isinstance(raw_gaps, list) and len(raw_gaps) == 0):
        return SchemaResult(gaps=(), source=source)

    if not isinstance(raw_gaps, list):
        raise SchemaError(f"'gaps' in {source} must be a list, got {type(raw_gaps).__name__}")

    gaps = tuple(_parse_gap(g, i) for i, g in enumerate(raw_gaps))
    return SchemaResult(gaps=gaps, source=source)


def validate_gaps(gaps: tuple[Gap, ...]) -> list[str]:
    """Validate a collection of gaps for logical consistency.

    Returns a list of error strings. Empty list means all valid.
    Does NOT raise — caller decides whether errors are fatal.

    Checks:
    1. Unique IDs — no duplicate gap IDs
    2. Status/timestamp coherence:
       - verified → last_verified must be non-None
       - unknown → last_verified must be None
    3. Reference integrity — all IDs in blocks/blocked_by exist in the schema
    4. No self-references — a gap cannot block itself
    5. Priority range — must be 1-5
    6. TTL range — if set, must be >= 1
    """
    errors: list[str] = []
    all_ids: set[str] = set()
    seen_ids: set[str] = set()

    # Collect all valid IDs first for reference checks
    for gap in gaps:
        all_ids.add(gap.id)

    for gap in gaps:
        # 1. Duplicate IDs
        if gap.id in seen_ids:
            errors.append(f"Duplicate gap ID: '{gap.id}'")
        seen_ids.add(gap.id)

        # 2. Status/timestamp coherence
        if gap.status is GapStatus.VERIFIED and gap.last_verified is None:
            errors.append(
                f"Gap '{gap.id}': status is 'verified' but last_verified is None"
            )
        if gap.status is GapStatus.UNKNOWN and gap.last_verified is not None:
            errors.append(
                f"Gap '{gap.id}': status is 'unknown' but last_verified is set"
            )

        # 3. Reference integrity + 4. Self-references
        for ref in gap.blocks:
            if ref == gap.id:
                errors.append(f"Gap '{gap.id}' references itself in 'blocks'")
            elif ref not in all_ids:
                errors.append(
                    f"Gap '{gap.id}' blocks unknown gap '{ref}'"
                )
        for ref in gap.blocked_by:
            if ref == gap.id:
                errors.append(f"Gap '{gap.id}' references itself in 'blocked_by'")
            elif ref not in all_ids:
                errors.append(
                    f"Gap '{gap.id}' blocked_by unknown gap '{ref}'"
                )

        # 5. Priority range
        if gap.priority < 1 or gap.priority > 5:
            errors.append(
                f"Gap '{gap.id}': priority {gap.priority} outside range 1-5"
            )

        # 6. TTL range
        if gap.ttl_days is not None and gap.ttl_days < 1:
            errors.append(
                f"Gap '{gap.id}': ttl_days {gap.ttl_days} must be >= 1"
            )

    return errors
