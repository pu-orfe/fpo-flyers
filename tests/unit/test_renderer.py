"""Tests for flyer renderer."""

from datetime import datetime, timezone
from pathlib import Path

from fpo_flyers.models import CommitteeMember, FPOEvent
from fpo_flyers.renderer import TEMPLATES_DIR, render_html, render_html_flyer, render_ipad_html


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
        assert "1:00 pm in Sherrerd Hall, Room 125" in html

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


class TestRenderIpadHtml:
    def test_contains_viewport_meta(self):
        html = render_ipad_html(_sample_event())
        assert 'name="viewport"' in html

    def test_contains_candidate_name(self):
        html = render_ipad_html(_sample_event())
        assert "Shange Tang" in html

    def test_contains_date(self):
        html = render_ipad_html(_sample_event())
        assert "Monday, March 2, 2026" in html

    def test_contains_dissertation_title(self):
        html = render_ipad_html(_sample_event())
        assert "From Representation to Reasoning" in html

    def test_contains_committee(self):
        html = render_ipad_html(_sample_event())
        assert "Jianqing Fan, (Chair)" in html

    def test_contains_pdf_link(self):
        html = render_ipad_html(_sample_event())
        assert "Shange_Tang.pdf" in html

    def test_uses_clamp_sizing(self):
        html = render_ipad_html(_sample_event())
        assert "clamp(" in html


class TestRenderHtmlFlyer:
    def test_writes_html_file(self, tmp_path):
        path = render_html_flyer(_sample_event(), tmp_path)
        assert path.exists()
        assert path.suffix == ".html"
        assert path.name == "Shange_Tang.html"

    def test_html_file_content(self, tmp_path):
        path = render_html_flyer(_sample_event(), tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "Shange Tang" in content
        assert "viewport" in content

    def test_creates_output_dir(self, tmp_path):
        out = tmp_path / "nested" / "dir"
        path = render_html_flyer(_sample_event(), out)
        assert path.exists()
