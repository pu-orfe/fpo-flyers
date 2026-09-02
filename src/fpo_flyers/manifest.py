"""Publish a machine-readable index of the generated flyers.

WHY THIS EXISTS. The manifest used to be built in the CI workflow by listing `*.pdf`, so it
carried filenames and nothing else. Consumers therefore could not tell an upcoming FPO from
one that already happened - the ICS feed is not date-filtered, so past events keep producing
flyers - and the public slideshow was showing an FPO three weeks past. The generator already
holds every field on FPOEvent; it just threw them away at this step.

Filtering stays the CONSUMER's job. Flyers are still generated for past events because the
administrator may want to reprint one; a display chooses to skip them. That is why the date
is published rather than the event dropped.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import FPOEvent

MANIFEST_NAME = "manifest.json"


def manifest_entries(events: list[FPOEvent]) -> list[dict[str, str]]:
    """One entry per event, in feed order.

    `file` is the stem, not a filename with an extension: each event yields BOTH
    `<stem>.pdf` and `<stem>.html`, and consumers want different ones - the index links the
    PDF, the slideshow iframes the HTML. Publishing the stem stops every consumer having to
    strip an extension the previous format forced on them.

    `start` is ISO 8601 with an explicit offset. The feed's own datetimes are timezone-aware
    and the flyer viewer has a documented ambiguity about naive timestamps, so this never
    emits one.
    """
    return [
        {
            "file": e.safe_filename,
            "candidate": e.candidate_name,
            "start": e.start.isoformat(),
            "location": e.location,
        }
        for e in events
    ]


def write_manifest(events: list[FPOEvent], output_dir: Path) -> Path:
    """Write manifest.json alongside the flyers and return its path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / MANIFEST_NAME
    # Trailing newline so the file is diffable and shell-friendly, matching .feed_hash.
    path.write_text(
        json.dumps(manifest_entries(events), indent=2) + "\n", encoding="utf-8"
    )
    return path
