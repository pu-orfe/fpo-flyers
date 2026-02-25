"""Data models for FPO events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")


@dataclass
class CommitteeMember:
    """A member of the examining committee."""

    name: str
    is_chair: bool = False

    def __str__(self) -> str:
        if self.is_chair:
            return f"{self.name}, (Chair)"
        return self.name


@dataclass
class FPOEvent:
    """A Final Public Oral examination event."""

    uid: str
    candidate_name: str
    start: datetime
    end: datetime
    location: str
    committee: list[CommitteeMember] = field(default_factory=list)
    dissertation_title: str = ""
    dissertation_pdf_url: str = ""
    event_url: str = ""
    description_raw: str = ""

    @property
    def start_eastern(self) -> datetime:
        """Start time in US/Eastern."""
        return self.start.astimezone(EASTERN)

    @property
    def end_eastern(self) -> datetime:
        """End time in US/Eastern."""
        return self.end.astimezone(EASTERN)

    @property
    def formatted_date(self) -> str:
        """e.g. 'Monday, March 2, 2026'."""
        return self.start_eastern.strftime("%A, %B %-d, %Y")

    @property
    def formatted_time(self) -> str:
        """e.g. '1:00 pm'."""
        t = self.start_eastern
        hour = t.hour % 12 or 12
        minute = f":{t.minute:02d}" if t.minute else ""
        period = "am" if t.hour < 12 else "pm"
        return f"{hour}{minute} {period}"

    @property
    def formatted_location(self) -> str:
        """Reformat '125 - Sherrerd Hall' to 'Sherrerd Hall, Room 125'."""
        loc = self.location.strip()
        if " - " in loc:
            room, building = loc.split(" - ", 1)
            return f"{building}, Room {room}"
        return loc

    @property
    def formatted_time_location(self) -> str:
        """e.g. '1:00 pm in Sherrerd Hall, Room 125'."""
        return f"{self.formatted_time} in {self.formatted_location}"

    @property
    def committee_text(self) -> str:
        """Format committee for the flyer.

        e.g. 'Professors Jianqing Fan, (Chair)\nElizaveta Rebrova, and Jason Klusowski'
        """
        if not self.committee:
            return ""
        parts: list[str] = []
        for i, member in enumerate(self.committee):
            is_last = i == len(self.committee) - 1
            if i == 0:
                prefix = "Professors " if len(self.committee) > 1 else "Professor "
                suffix = str(member)
            else:
                prefix = "and " if is_last else ""
                suffix = str(member)
            parts.append(f"{prefix}{suffix}")
        # Chair on first line, rest joined with commas
        lines: list[str] = []
        first = parts[0]
        rest = parts[1:]
        if rest:
            lines.append(f"{first}")
            lines.append(", ".join(rest))
        else:
            lines.append(first)
        return "\n".join(lines)

    @property
    def safe_filename(self) -> str:
        """Filename-safe version of candidate name."""
        return self.candidate_name.replace(" ", "_").replace("/", "_")
