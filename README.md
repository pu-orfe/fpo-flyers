# FPO Flyers

Automated generation of Final Public Oral (FPO) examination flyers.

Fetches events from the department ICS feed, scrapes dissertation titles from event pages, and produces styled PDF flyers.

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

| Setting | Type | Where to set | Format |
|---------|------|--------------|--------|
| `ICS_FEED_URL` | Repo variable | Settings → Secrets and variables → Actions → Variables | Full URL to the ICS feed |
| `BYPASS_HEADER` | Repo secret | Settings → Secrets and variables → Actions → Secrets | `Name: Value` (ask a maintainer for the value) |

Both are optional. If `ICS_FEED_URL` is unset the built-in default is used. If `BYPASS_HEADER` is unset the scraper sends no extra headers.

For local runs, pass them on the command line:

```bash
fpo-flyers --output-dir output --force --verbose \
  --feed-url "https://..." \
  --bypass-header "Header-Name: header-value"
```

## HTML Flyer Background Colors

The HTML (iPad) version of each flyer supports an optional background color, selectable via the color dots on the index page or by appending `?bg=<name>` to the flyer URL. All colors are rendered at 7% opacity to keep text legible.

| # | Name  | RGB                  |
|---|-------|----------------------|
| 1 | Gold  | `rgb(201,140,32)`    |
| 2 | Olive | `rgb(197,184,98)`    |
| 3 | Tan   | `rgb(227,208,162)`   |
| 4 | Sage  | `rgb(142,171,136)`   |
| 5 | Teal  | `rgb(127,155,163)`   |
| 6 | Plum  | `rgb(141,120,153)`   |
| 7 | Rose  | `rgb(182,134,131)`   |

## CI/CD

The GitHub Actions workflow runs every 30 minutes and can be triggered manually. When the feed changes, it generates PDFs and deploys them to GitHub Pages.

Trigger manually with force regeneration:
**Actions → Generate FPO Flyers → Run workflow → check "Force regeneration"**
