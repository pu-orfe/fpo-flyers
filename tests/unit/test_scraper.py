"""Tests for event page scraper."""

import responses

from fpo_flyers.scraper import parse_event_html, scrape_event_page


class TestParseEventHtml:
    def test_extracts_title(self, sample_event_html):
        result = parse_event_html(sample_event_html)
        assert result["dissertation_title"] == (
            "From Representation to Reasoning: Theoretical Guarantees "
            "and Frontier Systems in Modern Machine Learning"
        )

    def test_extracts_pdf_url(self, sample_event_html):
        result = parse_event_html(sample_event_html)
        assert "dropbox.com" in result["dissertation_pdf_url"]
        assert "Thesis-Shange-Tang.pdf" in result["dissertation_pdf_url"]

    def test_missing_fields(self):
        html = "<html><body><h1>No FPO data</h1></body></html>"
        result = parse_event_html(html)
        assert result["dissertation_title"] == ""
        assert result["dissertation_pdf_url"] == ""


class TestScrapeEventPage:
    @responses.activate
    def test_scrape_success(self, sample_event_html):
        url = "https://orfe.princeton.edu/events/2026/fpo-shange-tang"
        responses.add(responses.GET, url, body=sample_event_html, status=200)
        result = scrape_event_page(url)
        assert "Representation" in result["dissertation_title"]

    @responses.activate
    def test_scrape_sends_extra_headers(self, sample_event_html):
        url = "https://orfe.princeton.edu/events/2026/fpo-shange-tang"
        responses.add(responses.GET, url, body=sample_event_html, status=200)
        scrape_event_page(url, extra_headers={"x-custom": "secret"})
        assert responses.calls[0].request.headers["x-custom"] == "secret"

    @responses.activate
    def test_scrape_no_extra_headers(self, sample_event_html):
        url = "https://orfe.princeton.edu/events/2026/fpo-shange-tang"
        responses.add(responses.GET, url, body=sample_event_html, status=200)
        scrape_event_page(url)
        assert "x-custom" not in responses.calls[0].request.headers
