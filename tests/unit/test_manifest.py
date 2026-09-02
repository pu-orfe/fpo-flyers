"""Tests for the published flyer manifest.

The manifest used to be assembled in CI from `ls *.pdf`, so it carried filenames and nothing
else. Consumers therefore could not tell an upcoming FPO from one that had already happened -
the feed is not date-filtered - and the public slideshow was showing an FPO three weeks past.
These tests pin the fields that fixed that.
"""

import json
from datetime import datetime, timezone

from fpo_flyers.manifest import manifest_entries, write_manifest
from fpo_flyers.models import FPOEvent
from fpo_flyers.renderer import render_html_flyer, render_pdf


def _event(name="Shange Tang", when=datetime(2026, 3, 2, 18, 0, tzinfo=timezone.utc)):
    return FPOEvent(
        uid=f"uid-{name}",
        candidate_name=name,
        start=when,
        end=when,
        location="125 - Sherrerd Hall",
    )


def test_entry_carries_the_start_time():
    """The whole point of the change: without a date, a display cannot skip a past FPO."""
    entry = manifest_entries([_event()])[0]
    assert entry["start"] == "2026-03-02T18:00:00+00:00"


def test_start_always_has_an_explicit_offset():
    """A naive timestamp is ambiguous, and the flyer viewer's own README and implementation
    disagree about how to read one - it documents Eastern and parses UTC. Never emit one."""
    for entry in manifest_entries([_event(), _event("Jane Doe")]):
        assert entry["start"].endswith(("+00:00", "-05:00", "-04:00")), entry["start"]


def test_entry_carries_candidate_and_location():
    entry = manifest_entries([_event()])[0]
    assert entry["candidate"] == "Shange Tang"
    assert entry["location"] == "125 - Sherrerd Hall"


def test_file_is_a_stem_not_a_filename():
    """Each event yields both a .pdf and a .html and different consumers want different
    ones - the index links the PDF, the slideshow iframes the HTML. Publishing the stem
    stops every consumer stripping an extension."""
    entry = manifest_entries([_event()])[0]
    assert entry["file"] == "Shange_Tang"
    assert not entry["file"].endswith((".pdf", ".html"))


def test_manifest_order_follows_the_feed():
    names = [e["candidate"] for e in manifest_entries([_event("A"), _event("B"), _event("C")])]
    assert names == ["A", "B", "C"]


def test_empty_feed_writes_valid_json(tmp_path):
    """CI copies whatever is here to Pages, and the page fetches it unconditionally: an
    absent or malformed manifest blanks the display."""
    path = write_manifest([], tmp_path)
    assert json.loads(path.read_text()) == []


def test_written_file_is_valid_json_with_a_trailing_newline(tmp_path):
    path = write_manifest([_event()], tmp_path)
    text = path.read_text()
    assert text.endswith("\n")
    assert len(json.loads(text)) == 1


def test_manifest_stem_matches_the_files_actually_rendered(tmp_path):
    """A stem that does not match the rendered filenames is a 404 on the display, and the
    two are produced by different functions - so agreement is asserted, not assumed."""
    event = _event("Ana-María O'Neill")
    render_pdf(event, tmp_path)
    render_html_flyer(event, tmp_path)
    stem = manifest_entries([event])[0]["file"]
    assert (tmp_path / f"{stem}.pdf").is_file(), f"no PDF for stem {stem!r}"
    assert (tmp_path / f"{stem}.html").is_file(), f"no HTML for stem {stem!r}"
