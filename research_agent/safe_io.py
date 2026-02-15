"""Atomic file writing for safe state persistence.

Prevents partial writes from corrupting state files (risks F3.3, F4.4).
Writes to a temporary file in the same directory, then atomically renames.
"""

import os
import tempfile
from pathlib import Path

from .errors import StateError


def atomic_write(path: Path | str, content: str, encoding: str = "utf-8") -> None:
    """Write content to a file atomically.

    Writes to a temporary file in the same directory, then renames.
    If the write fails for any reason, the original file is unchanged.

    Args:
        path: Target file path.
        content: Content to write.
        encoding: File encoding (default utf-8).

    Raises:
        StateError: If the write fails (wraps underlying OSError).
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd = None
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding=encoding) as f:
            fd = None  # os.fdopen takes ownership of the fd
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp_path, target)
    except OSError as exc:
        # Clean up temp file on failure
        if tmp_path is not None and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        if fd is not None:
            os.close(fd)
        raise StateError(f"Failed to write {target}: {exc}") from exc
