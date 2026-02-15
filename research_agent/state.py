"""State persistence for gap schema — atomic YAML writes and single-gap updates."""

from dataclasses import replace
from pathlib import Path

import yaml

from .errors import SchemaError, StateError
from .safe_io import atomic_write
from .schema import Gap, GapStatus, load_schema, validate_gaps


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
    "metadata": {},
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


def update_gap(
    path: Path | str,
    gap_id: str,
    **changes: object,
) -> Gap:
    """Load schema, update one gap's fields, validate, and save.

    Since Gap is frozen, constructs a new Gap with the updated fields.
    Re-validates the full gap set after mutation to ensure consistency.

    Args:
        path: Path to the YAML schema file.
        gap_id: ID of the gap to update.
        **changes: Field names and new values (e.g., status=GapStatus.VERIFIED).

    Returns:
        The updated Gap object.

    Raises:
        StateError: If the gap_id is not found in the schema.
        SchemaError: If the updated schema fails validation.
    """
    result = load_schema(path)
    gaps = result.gaps

    updated_gap: Gap | None = None
    new_gaps: list[Gap] = []

    for gap in gaps:
        if gap.id == gap_id:
            updated_gap = replace(gap, **changes)
            new_gaps.append(updated_gap)
        else:
            new_gaps.append(gap)

    if updated_gap is None:
        raise StateError(f"Gap '{gap_id}' not found in {path}")

    new_gaps_tuple = tuple(new_gaps)
    errors = validate_gaps(new_gaps_tuple)
    if errors:
        raise SchemaError(
            f"Validation failed after updating gap '{gap_id}'",
            errors=errors,
        )

    save_schema(path, new_gaps_tuple)
    return updated_gap
