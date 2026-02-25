"""CLI entrypoint for FPO flyer generation."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from .change_detection import has_changed, write_hash
from .feed import FEED_URL, compute_feed_hash, fetch_feed, parse_events
from .renderer import render_pdf
from .scraper import scrape_event_page

logger = logging.getLogger("fpo_flyers")


@click.command()
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("output"),
    help="Directory for generated PDFs.",
)
@click.option(
    "--hash-file",
    type=click.Path(path_type=Path),
    default=Path(".feed_hash"),
    help="Path to the feed hash file.",
)
@click.option("--force", is_flag=True, help="Skip change detection.")
@click.option("--verbose", is_flag=True, help="Enable verbose logging.")
@click.option("--feed-url", default=FEED_URL, help="ICS feed URL.")
@click.option(
    "--bypass-header",
    default=None,
    help='Header for event page scraping, as "Name: Value".',
)
def main(
    output_dir: Path,
    hash_file: Path,
    force: bool,
    verbose: bool,
    feed_url: str,
    bypass_header: str | None,
) -> None:
    """Generate FPO flyer PDFs from the Princeton ORFE ICS feed."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    # Parse bypass header into a dict
    extra_headers: dict[str, str] | None = None
    if bypass_header:
        if ":" not in bypass_header:
            raise click.BadParameter(
                f"Expected 'Name: Value' format, got: {bypass_header!r}",
                param_hint="'--bypass-header'",
            )
        name, value = bypass_header.split(":", 1)
        extra_headers = {name.strip(): value.strip()}

    logger.info("Fetching ICS feed from %s", feed_url)
    ics_text = fetch_feed(feed_url)
    current_hash = compute_feed_hash(ics_text)

    if not force and not has_changed(current_hash, hash_file):
        logger.info("Feed unchanged (hash %s). Nothing to do.", current_hash[:12])
        sys.exit(0)

    logger.info("Feed changed or --force used. Generating flyers...")
    events = parse_events(ics_text)
    if not events:
        logger.warning("No FPO events found in feed.")
        sys.exit(0)

    logger.info("Found %d event(s)", len(events))
    for event in events:
        logger.info("Processing: %s", event.candidate_name)
        if event.event_url:
            try:
                info = scrape_event_page(event.event_url, extra_headers)
                event.dissertation_title = info["dissertation_title"]
                event.dissertation_pdf_url = info["dissertation_pdf_url"]
                logger.debug(
                    "  Title: %s", event.dissertation_title or "(not found)"
                )
            except Exception:
                logger.warning(
                    "  Could not scrape event page: %s", event.event_url
                )

        pdf_path = render_pdf(event, output_dir)
        logger.info("  Generated: %s", pdf_path)

    write_hash(hash_file, current_hash)
    logger.info("Hash updated: %s", current_hash[:12])
    logger.info("Done. %d flyer(s) in %s", len(events), output_dir)
