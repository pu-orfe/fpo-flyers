"""Tests for flyer renderer."""

from datetime import datetime, timezone
from pathlib import Path

from fpo_flyers.models import CommitteeMember, FPOEvent
from fpo_flyers.renderer import TEMPLATES_DIR, render_html


def _sample_event() -> FPOEvent:
    return FPOEvent(
        uid="test-uid",
        candidate_name="Shange Tang",
        start=datetime(2026, 3, 2, 18, 0, tzinfo=timezone.utc),
        end=datetime(2026, 3, 2, 21, 0, tzinfo=timezone.utc),
        location="125 - Sherrerd Hall",
        committee=[
            CommitteeMember("Jianqing Fan", is_chair=True),
            CommitteeMember("Elizaveta Rebrova"),
            CommitteeMember("Jason Klusowski"),
        ],
        dissertation_title=(
            "From Representation to Reasoning: Theoretical Guarantees "
            "and Frontier Systems in Modern Machine Learning"
        ),
    )


class TestRenderHtml:
    def test_contains_announcement(self):
        html = render_html(_sample_event())
        assert "Announcement" in html

    def test_contains_candidate_name(self):
        html = render_html(_sample_event())
        assert "Shange Tang" in html

    def test_contains_date(self):
        html = render_html(_sample_event())
        assert "Monday, March 2, 2026" in html

    def test_contains_time_location(self):
        html = render_html(_sample_event())
        assert "1 pm in Sherrerd Hall, Room 125" in html

    def test_contains_dissertation_title(self):
        html = render_html(_sample_event())
        assert "From Representation to Reasoning" in html

    def test_contains_committee(self):
        html = render_html(_sample_event())
        assert "Jianqing Fan, (Chair)" in html
        assert "Elizaveta Rebrova" in html
        assert "Jason Klusowski" in html

    def test_contains_encouragement(self):
        html = render_html(_sample_event())
        assert "encouraged to attend" in html

    def test_curly_quotes_around_title(self):
        html = render_html(_sample_event())
        assert "&ldquo;" in html  # left double curly quote entity
        assert "&rdquo;" in html  # right double curly quote entity
