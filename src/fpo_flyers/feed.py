"""ICS feed fetching, parsing, and hashing."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

import requests
from icalendar import Calendar

from .models import CommitteeMember, FPOEvent

FEED_URL = "https://orfe.princeton.edu/feeds/events/ical.ics?tid=491"


def fetch_feed(url: str = FEED_URL) -> str:
    """Fetch the raw ICS feed text."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_committee(description: str) -> list[CommitteeMember]:
    """Parse committee members from the DESCRIPTION field.

    Example input:
      "The examining committee members are Professors Jianqing Fan
       (Chair of the Committee), Liza Rebrova, and Jason Klusowski."
    """
    # Strip the preamble
    match = re.search(
        r"(?:Professors?|Prof\.)\s+(.+)",
        description,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return []

    text = match.group(1).strip().rstrip(".")
    # Split on commas and "and"
    # First, normalize "and" preceded by comma or standalone
    text = re.sub(r",?\s+and\s+", ", ", text)
    parts = [p.strip() for p in text.split(",") if p.strip()]

    members: list[CommitteeMember] = []
    for part in parts:
        is_chair = False
        if "(Chair" in part:
            is_chair = True
            part = re.sub(r"\s*\(Chair[^)]*\)", "", part).strip()
        if part:
            members.append(CommitteeMember(name=part, is_chair=is_chair))
    return members


def extract_candidate_name(summary: str) -> str:
    """Extract candidate name from SUMMARY like 'FPO, Shange Tang'."""
    if "," in summary:
        return summary.split(",", 1)[1].strip()
    return summary.strip()


def parse_events(ics_text: str) -> list[FPOEvent]:
    """Parse ICS text into a list of FPOEvent objects."""
    cal = Calendar.from_ical(ics_text)
    events: list[FPOEvent] = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        summary = str(component.get("SUMMARY", ""))
        uid = str(component.get("UID", ""))
        location = str(component.get("LOCATION", ""))
        description = str(component.get("DESCRIPTION", ""))
        url = str(component.get("URL", ""))

        dt_start = component.get("DTSTART")
        dt_end = component.get("DTEND")
        start = dt_start.dt if dt_start else datetime.now(timezone.utc)
        end = dt_end.dt if dt_end else start

        # Ensure timezone-aware
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        candidate = extract_candidate_name(summary)
        committee = parse_committee(description)

        events.append(
            FPOEvent(
                uid=uid,
                candidate_name=candidate,
                start=start,
                end=end,
                location=location,
                committee=committee,
                event_url=url,
                description_raw=description,
            )
        )
    return events


def compute_feed_hash(ics_text: str) -> str:
    """Compute SHA-256 hash of the feed, excluding DTSTAMP lines."""
    lines = ics_text.splitlines()
    filtered = [line for line in lines if not line.startswith("DTSTAMP")]
    content = "\n".join(filtered)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
