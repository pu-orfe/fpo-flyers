"""Integration test: full pipeline with mocked HTTP."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
import responses

from fpo_flyers.change_detection import read_stored_hash
from fpo_flyers.feed import FEED_URL, compute_feed_hash, fetch_feed, parse_events
from fpo_flyers.renderer import render_pdf
from fpo_flyers.scraper import scrape_event_page


@responses.activate
def test_full_pipeline(sample_feed_ics, sample_event_html, tmp_path):
    """End-to-end: fetch feed → parse → scrape → render PDF."""
    # Mock the ICS feed
    responses.add(responses.GET, FEED_URL, body=sample_feed_ics, status=200)

    # Mock event pages
    responses.add(
        responses.GET,
        "https://orfe.princeton.edu/events/2026/fpo-shange-tang",
        body=sample_event_html,
        status=200,
    )
    responses.add(
        responses.GET,
        "https://orfe.princeton.edu/events/2026/fpo-jane-doe",
        body=sample_event_html,
        status=200,
    )

    # Fetch and parse
    ics_text = fetch_feed()
    events = parse_events(ics_text)
    assert len(events) == 2

    # Scrape each event page (pass extra_headers like the CLI would)
    for event in events:
        info = scrape_event_page(event.event_url, extra_headers={"x-test": "1"})
        event.dissertation_title = info["dissertation_title"]
        event.dissertation_pdf_url = info["dissertation_pdf_url"]

    # Render PDFs
    output_dir = tmp_path / "output"
    for event in events:
        pdf_path = render_pdf(event, output_dir)
        assert pdf_path.exists()
        assert pdf_path.suffix == ".pdf"
        assert pdf_path.stat().st_size > 0

    # Verify hash
    feed_hash = compute_feed_hash(ics_text)
    assert len(feed_hash) == 64


@pytest.mark.integration
def test_live_feed_fetch():
    """Fetch the live ICS feed (requires network)."""
    ics_text = fetch_feed()
    assert "VCALENDAR" in ics_text
    events = parse_events(ics_text)
    # Feed may be empty between FPO seasons, just check it parses
    assert isinstance(events, list)
