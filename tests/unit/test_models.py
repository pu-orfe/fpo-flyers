"""Tests for data models."""

from datetime import datetime, timezone

from fpo_flyers.models import EASTERN, CommitteeMember, FPOEvent


def _make_event(**kwargs) -> FPOEvent:
    defaults = {
        "uid": "test-uid-1",
        "candidate_name": "Shange Tang",
        # 2026-03-02 18:00 UTC = 2026-03-02 13:00 ET
        "start": datetime(2026, 3, 2, 18, 0, tzinfo=timezone.utc),
        "end": datetime(2026, 3, 2, 19, 30, tzinfo=timezone.utc),
        "location": "125 - Sherrerd Hall",
    }
    defaults.update(kwargs)
    return FPOEvent(**defaults)


class TestCommitteeMember:
    def test_str_regular(self):
        m = CommitteeMember(name="Elizaveta Rebrova")
        assert str(m) == "Elizaveta Rebrova"

    def test_str_chair(self):
        m = CommitteeMember(name="Jianqing Fan", is_chair=True)
        assert str(m) == "Jianqing Fan, (Chair)"


class TestFPOEvent:
    def test_start_eastern(self):
        event = _make_event()
        eastern = event.start_eastern
        assert eastern.tzinfo == EASTERN
        assert eastern.hour == 13  # 18 UTC = 13 ET in March (EST)

    def test_formatted_date(self):
        event = _make_event()
        assert event.formatted_date == "Monday, March 2, 2026"

    def test_formatted_time(self):
        event = _make_event()
        assert event.formatted_time == "1 pm"

    def test_formatted_time_with_minutes(self):
        event = _make_event(
            start=datetime(2026, 3, 2, 18, 30, tzinfo=timezone.utc)
        )
        assert event.formatted_time == "1:30 pm"

    def test_formatted_time_morning(self):
        event = _make_event(
            start=datetime(2026, 3, 2, 15, 0, tzinfo=timezone.utc)
        )
        assert event.formatted_time == "10 am"

    def test_formatted_location(self):
        event = _make_event()
        assert event.formatted_location == "Sherrerd Hall, Room 125"

    def test_formatted_location_no_dash(self):
        event = _make_event(location="Friend Center 101")
        assert event.formatted_location == "Friend Center 101"

    def test_formatted_time_location(self):
        event = _make_event()
        assert event.formatted_time_location == "1 pm in Sherrerd Hall, Room 125"

    def test_committee_text_full(self):
        event = _make_event(
            committee=[
                CommitteeMember("Jianqing Fan", is_chair=True),
                CommitteeMember("Elizaveta Rebrova"),
                CommitteeMember("Jason Klusowski"),
            ]
        )
        expected = (
            "Professors Jianqing Fan, (Chair)\n"
            "Elizaveta Rebrova, and Jason Klusowski"
        )
        assert event.committee_text == expected

    def test_committee_text_single(self):
        event = _make_event(
            committee=[CommitteeMember("Jianqing Fan", is_chair=True)]
        )
        assert event.committee_text == "Professor Jianqing Fan, (Chair)"

    def test_committee_text_empty(self):
        event = _make_event()
        assert event.committee_text == ""

    def test_safe_filename(self):
        event = _make_event(candidate_name="Shange Tang")
        assert event.safe_filename == "Shange_Tang"

    def test_safe_filename_with_slash(self):
        event = _make_event(candidate_name="A/B Test")
        assert event.safe_filename == "A_B_Test"
