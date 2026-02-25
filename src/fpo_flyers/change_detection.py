"""Change detection via SHA-256 hash file comparison."""

from __future__ import annotations

from pathlib import Path

DEFAULT_HASH_FILE = ".feed_hash"


def read_stored_hash(hash_file: Path) -> str:
    """Read the previously stored hash, or return empty string if missing."""
    if hash_file.exists():
        return hash_file.read_text().strip()
    return ""


def write_hash(hash_file: Path, feed_hash: str) -> None:
    """Write the current hash to the hash file."""
    hash_file.write_text(feed_hash + "\n")


def has_changed(current_hash: str, hash_file: Path) -> bool:
    """Return True if the feed has changed since last run."""
    stored = read_stored_hash(hash_file)
    return current_hash != stored
