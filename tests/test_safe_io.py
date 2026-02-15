"""Tests for atomic file writer."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from research_agent.errors import StateError
from research_agent.safe_io import atomic_write


class TestAtomicWrite:
    def test_atomic_write_creates_file(self, tmp_path):
        """New file created with correct content."""
        target = tmp_path / "output.txt"
        atomic_write(target, "hello world")
        assert target.read_text() == "hello world"

    def test_atomic_write_overwrites_existing(self, tmp_path):
        """Existing file replaced with new content."""
        target = tmp_path / "output.txt"
        target.write_text("old content")
        atomic_write(target, "new content")
        assert target.read_text() == "new content"

    def test_atomic_write_no_partial_on_error(self, tmp_path):
        """Simulated write failure leaves original file unchanged."""
        target = tmp_path / "output.txt"
        target.write_text("original")

        with patch("research_agent.safe_io.os.fdopen", side_effect=OSError("disk full")):
            with pytest.raises(StateError):
                atomic_write(target, "should not appear")

        assert target.read_text() == "original"

    def test_atomic_write_creates_parent_dirs(self, tmp_path):
        """Non-existent parent directories created automatically."""
        target = tmp_path / "deep" / "nested" / "dir" / "file.txt"
        atomic_write(target, "deep content")
        assert target.read_text() == "deep content"

    def test_atomic_write_cleans_temp_on_failure(self, tmp_path):
        """No orphaned temp files after failure."""
        target = tmp_path / "output.txt"

        with patch("research_agent.safe_io.os.fdopen", side_effect=OSError("fail")):
            with pytest.raises(StateError):
                atomic_write(target, "content")

        # No .tmp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == [], f"Orphaned temp files: {tmp_files}"

    def test_atomic_write_raises_state_error(self, tmp_path):
        """OSError wrapped in StateError."""
        target = tmp_path / "output.txt"

        with patch("research_agent.safe_io.os.fdopen", side_effect=OSError("boom")):
            with pytest.raises(StateError, match="Failed to write") as exc_info:
                atomic_write(target, "content")
            assert exc_info.value.__cause__ is not None
            assert isinstance(exc_info.value.__cause__, OSError)

    def test_atomic_write_preserves_encoding(self, tmp_path):
        """UTF-8 content with special characters survives round-trip."""
        target = tmp_path / "unicode.txt"
        content = "日本語テスト 🎵 café résumé naïve"
        atomic_write(target, content)
        assert target.read_text(encoding="utf-8") == content

    def test_atomic_write_accepts_str_path(self, tmp_path):
        """Works with string paths, not just Path objects."""
        target = str(tmp_path / "string_path.txt")
        atomic_write(target, "string path content")
        assert Path(target).read_text() == "string path content"
