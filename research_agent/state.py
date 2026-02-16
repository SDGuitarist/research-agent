"""State persistence for gap schema — atomic YAML writes and single-gap updates."""

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .safe_io import atomic_write
from .schema import Gap, GapStatus


# Fields that are always included in YAML output (required by _parse_gap)
_REQUIRED_FIELDS = {"id", "category"}

# Default values — fields matching these are omitted from YAML to keep it clean
_DEFAULTS: dict[str, object] = {
    "status": GapStatus.UNKNOWN,
    "priority": 3,
    "last_verified": None,
    "last_checked": None,
    "ttl_days": None,
    "blocks": (),
    "blocked_by": (),
    "findings": "",
}


def _gap_to_dict(gap: Gap) -> dict:
    """Convert a Gap to a YAML-serializable dict.

    Converts GapStatus enum to its string value, tuples to lists,
    and omits fields that are at their default values to keep YAML clean.
    """
    result: dict[str, object] = {}

    result["id"] = gap.id
    result["category"] = gap.category

    for field_name, default_val in _DEFAULTS.items():
        value = getattr(gap, field_name)
        if value == default_val:
            continue
        if isinstance(value, GapStatus):
            result[field_name] = value.value
        elif isinstance(value, tuple):
            result[field_name] = list(value)
        else:
            result[field_name] = value

    return result


def save_schema(path: Path | str, gaps: tuple[Gap, ...]) -> None:
    """Write gaps to a YAML schema file atomically.

    Args:
        path: Target file path.
        gaps: Gap objects to serialize.

    Raises:
        StateError: If the write fails (via atomic_write).
    """
    data = {"gaps": [_gap_to_dict(g) for g in gaps]}
    content = yaml.dump(data, default_flow_style=False, sort_keys=False)
    atomic_write(path, content)


def mark_checked(gap: Gap, now: datetime | None = None) -> Gap:
    """Return a new Gap with last_checked set to now.

    Updates last_checked only. Does NOT change status or last_verified.
    Use when a gap was researched but no new findings were found.

    Args:
        gap: The gap to update.
        now: Override timestamp for testing. Defaults to UTC now.

    Returns:
        New Gap with updated last_checked.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    return replace(gap, last_checked=now.isoformat())


def mark_verified(gap: Gap, now: datetime | None = None) -> Gap:
    """Return a new Gap with status=VERIFIED and timestamps set to now.

    Updates last_verified, last_checked, and status. Use when a gap
    was researched and new findings were confirmed.

    Args:
        gap: The gap to update.
        now: Override timestamp for testing. Defaults to UTC now.

    Returns:
        New Gap with status=VERIFIED and fresh timestamps.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    ts = now.isoformat()
    return replace(gap, status=GapStatus.VERIFIED, last_verified=ts, last_checked=ts)
