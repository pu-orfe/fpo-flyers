"""Tests for change detection."""

from pathlib import Path

from fpo_flyers.change_detection import has_changed, read_stored_hash, write_hash


class TestReadStoredHash:
    def test_missing_file(self, tmp_path):
        assert read_stored_hash(tmp_path / "nonexistent") == ""

    def test_existing_file(self, tmp_path):
        f = tmp_path / ".feed_hash"
        f.write_text("abc123\n")
        assert read_stored_hash(f) == "abc123"


class TestWriteHash:
    def test_creates_file(self, tmp_path):
        f = tmp_path / ".feed_hash"
        write_hash(f, "deadbeef")
        assert f.read_text() == "deadbeef\n"

    def test_overwrites_file(self, tmp_path):
        f = tmp_path / ".feed_hash"
        f.write_text("old\n")
        write_hash(f, "new")
        assert f.read_text() == "new\n"


class TestHasChanged:
    def test_no_previous_hash(self, tmp_path):
        assert has_changed("abc", tmp_path / "missing") is True

    def test_same_hash(self, tmp_path):
        f = tmp_path / ".feed_hash"
        f.write_text("abc\n")
        assert has_changed("abc", f) is False

    def test_different_hash(self, tmp_path):
        f = tmp_path / ".feed_hash"
        f.write_text("abc\n")
        assert has_changed("xyz", f) is True
