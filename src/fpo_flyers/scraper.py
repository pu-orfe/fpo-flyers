"""Scrape event web pages for dissertation title and PDF link."""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup


def scrape_event_page(
    url: str,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, str]:
    """Scrape an event page for dissertation title and PDF URL.

    Returns a dict with keys 'dissertation_title' and 'dissertation_pdf_url'.
    """
    headers = dict(extra_headers) if extra_headers else {}
    resp = requests.get(
        url,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    return parse_event_html(resp.text)


def parse_event_html(html: str) -> dict[str, str]:
    """Parse event page HTML for dissertation info."""
    soup = BeautifulSoup(html, "html.parser")
    result: dict[str, str] = {
        "dissertation_title": "",
        "dissertation_pdf_url": "",
    }

    # Dissertation title from event-subtitle div
    subtitle = soup.find(class_="event-subtitle")
    if subtitle:
        result["dissertation_title"] = subtitle.get_text(strip=True)

    # Dissertation PDF link from the virtual location field
    virtual_field = soup.find(
        class_="field--name-field-ps-events-location-virtual"
    )
    if virtual_field:
        link = virtual_field.find("a", href=True)
        if link:
            result["dissertation_pdf_url"] = link["href"]

    return result
