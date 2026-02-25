# FPO Flyers

Automated generation of Final Public Oral (FPO) examination flyers for
Princeton ORFE. Fetches events from the department ICS feed, scrapes
dissertation titles from event pages, and produces styled PDF flyers.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install ".[test]"
fpo-flyers --output-dir output --force --verbose
```

## Testing

```bash
# Unit tests
python -m pytest tests/unit/ -v

# Integration test (requires network)
python -m pytest tests/integration/ -v -m integration

# Docker
docker-compose run unit-tests
docker-compose run integration-tests
```

## Docker

```bash
# Generate flyers
docker-compose run generate

# Build production image
docker build -t fpo-flyers .
docker run -v "$(pwd)/output:/app/output" fpo-flyers --force --verbose
```

## Configuration

The ICS feed URL and event-page scraping header are configurable via
GitHub repo variables and secrets so nothing sensitive is committed to
the repository.

| Setting | Type | Where to set | Format |
|---------|------|--------------|--------|
| `ICS_FEED_URL` | Repo variable | Settings → Secrets and variables → Actions → Variables | Full URL to the ICS feed |
| `BYPASS_HEADER` | Repo secret | Settings → Secrets and variables → Actions → Secrets | `Name: Value` (ask a maintainer for the value) |

Both are optional. If `ICS_FEED_URL` is unset the built-in default is
used. If `BYPASS_HEADER` is unset the scraper sends no extra headers.

For local runs, pass them on the command line:

```bash
fpo-flyers --output-dir output --force --verbose \
  --feed-url "https://..." \
  --bypass-header "Header-Name: header-value"
```

## CI/CD

The GitHub Actions workflow runs on weekdays at noon UTC and can be
triggered manually. When the feed changes, it generates PDFs and
deploys them to GitHub Pages.

Trigger manually with force regeneration:
**Actions → Generate FPO Flyers → Run workflow → check "Force regeneration"**
