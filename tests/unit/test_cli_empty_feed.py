"""An empty feed must still record its hash.

Before this fix the CLI exited on "No FPO events found" without writing
.feed_hash, and the workflow only committed the hash when PDFs existed. The
stored hash therefore never matched an empty feed, so the check job reported
"changed" on every scheduled tick and the full build-and-deploy ran every 30
minutes for nothing.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from fpo_flyers.cli import main
from fpo_flyers.feed import compute_feed_hash

EMPTY_FEED = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//EN\r\nEND:VCALENDAR\r\n"


def _run(tmp_path: Path):
    hash_file = tmp_path / ".feed_hash"
    output_dir = tmp_path / "output"
    with patch("fpo_flyers.cli.fetch_feed", return_value=EMPTY_FEED):
        result = CliRunner().invoke(
            main, ["--output-dir", str(output_dir), "--hash-file", str(hash_file)]
        )
    return result, hash_file, output_dir


def test_empty_feed_writes_hash(tmp_path: Path) -> None:
    result, hash_file, _ = _run(tmp_path)
    assert result.exit_code == 0, result.output
    assert hash_file.exists(), "empty feed left .feed_hash unwritten"
    assert hash_file.read_text().strip() == compute_feed_hash(EMPTY_FEED)


def test_empty_feed_writes_empty_manifest(tmp_path: Path) -> None:
    result, _, output_dir = _run(tmp_path)
    assert result.exit_code == 0, result.output
    manifest = output_dir / "manifest.json"
    assert manifest.exists()
    assert json.loads(manifest.read_text()) == []


def test_unchanged_empty_feed_is_skipped(tmp_path: Path) -> None:
    """Second run against the same empty feed must not regenerate."""
    first, _, output_dir = _run(tmp_path)
    assert first.exit_code == 0, first.output
    (output_dir / "manifest.json").unlink()
    second, _, output_dir = _run(tmp_path)
    assert second.exit_code == 0, second.output
    assert not (output_dir / "manifest.json").exists(), "regenerated an unchanged feed"
