"""Tests for ICS feed parsing and hashing."""

import responses

from fpo_flyers.feed import (
    FEED_URL,
    compute_feed_hash,
    extract_candidate_name,
    fetch_feed,
    parse_committee,
    parse_events,
)


class TestExtractCandidateName:
    def test_standard(self):
        assert extract_candidate_name("FPO, Shange Tang") == "Shange Tang"

    def test_no_comma(self):
        assert extract_candidate_name("Shange Tang") == "Shange Tang"


class TestParseCommittee:
    def test_three_members_with_chair(self):
        desc = (
            "The examining committee members are Professors "
            "Jianqing Fan (Chair of the Committee), "
            "Liza Rebrova, and Jason Klusowski."
        )
        members = parse_committee(desc)
        assert len(members) == 3
        assert members[0].name == "Jianqing Fan"
        assert members[0].is_chair is True
        assert members[1].name == "Liza Rebrova"
        assert members[1].is_chair is False
        assert members[2].name == "Jason Klusowski"

    def test_empty_description(self):
        assert parse_committee("") == []

    def test_no_professors_keyword(self):
        assert parse_committee("Some random text") == []


class TestParseEvents:
    def test_parse_sample_feed(self, sample_feed_ics):
        events = parse_events(sample_feed_ics)
        assert len(events) == 2

        e = events[0]
        assert e.candidate_name == "Shange Tang"
        assert e.uid == "ps_events:12281:delta:0"
        assert e.location == "125 - Sherrerd Hall"
        assert len(e.committee) == 3
        assert e.committee[0].name == "Jianqing Fan"
        assert e.committee[0].is_chair is True
        assert e.event_url == "https://orfe.princeton.edu/events/2026/fpo-shange-tang"

    def test_parse_second_event(self, sample_feed_ics):
        events = parse_events(sample_feed_ics)
        e = events[1]
        assert e.candidate_name == "Jane Doe"
        assert e.location == "101 - Friend Center"


class TestFetchFeed:
    @responses.activate
    def test_fetch_success(self, sample_feed_ics):
        responses.add(responses.GET, FEED_URL, body=sample_feed_ics, status=200)
        result = fetch_feed()
        assert "VCALENDAR" in result

    @responses.activate
    def test_fetch_http_error(self):
        responses.add(responses.GET, FEED_URL, status=500)
        import pytest

        with pytest.raises(Exception):
            fetch_feed()


class TestComputeFeedHash:
    def test_deterministic(self, sample_feed_ics):
        h1 = compute_feed_hash(sample_feed_ics)
        h2 = compute_feed_hash(sample_feed_ics)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_ignores_dtstamp(self):
        feed_a = "BEGIN:VEVENT\nSUMMARY:Test\nDTSTAMP:20260101T000000Z\nEND:VEVENT"
        feed_b = "BEGIN:VEVENT\nSUMMARY:Test\nDTSTAMP:20260201T000000Z\nEND:VEVENT"
        assert compute_feed_hash(feed_a) == compute_feed_hash(feed_b)

    def test_detects_content_change(self):
        feed_a = "BEGIN:VEVENT\nSUMMARY:Test A\nEND:VEVENT"
        feed_b = "BEGIN:VEVENT\nSUMMARY:Test B\nEND:VEVENT"
        assert compute_feed_hash(feed_a) != compute_feed_hash(feed_b)
