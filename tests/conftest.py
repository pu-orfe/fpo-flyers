"""Shared test fixtures."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_feed_ics() -> str:
    return (FIXTURES_DIR / "sample_feed.ics").read_text()


@pytest.fixture
def sample_event_html() -> str:
    return (FIXTURES_DIR / "sample_event_page.html").read_text()
