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

The HTML (iPad) version of each flyer supports an optional background color, selectable via the color dots on the index page or by appending `?bg=<name>` to the flyer URL. All colors are rendered at 42% opacity.

| # | Name  | RGB                  |
|---|-------|----------------------|
| 1 | Gold  | `rgb(201,140,32)`    |
| 2 | Olive | `rgb(197,184,98)`    |
| 3 | Tan   | `rgb(227,208,162)`   |
| 4 | Sage  | `rgb(142,171,136)`   |
| 5 | Teal  | `rgb(127,155,163)`   |
| 6 | Plum  | `rgb(141,120,153)`   |
| 7 | Rose  | `rgb(182,134,131)`   |

## Dynamic View Page

The `view.html` page renders a flyer from URL query parameters, allowing external systems (e.g., Drupal) to link directly to a flyer without pre-generation.

**URL**: `https://pu-orfe.github.io/fpo-flyers/view.html?candidate=...&title=...&date=...&location=...&committee=...&bg=...`

| Parameter   | Required | Description |
|-------------|----------|-------------|
| `candidate` | Yes      | Candidate name. Accepts `"FPO, Name"` or just `"Name"`. |
| `title`     | No       | Dissertation title. |
| `date`      | No       | Start datetime — ISO 8601 (e.g., `2026-03-02T13:00:00`), treated as Eastern if no timezone, or Unix timestamp in seconds. |
| `location`  | No       | Location string (e.g., `125 - Sherrerd Hall`); automatically reformatted to `Sherrerd Hall, Room 125`. |
| `committee` | No       | Comma-separated names. Mark the chair with `(Chair)` or `(Chair of the Committee)` after their name. |
| `bg`        | No       | Background color name from the color table above. |

**Drupal webform integration** — In a Computed Twig element on the source entity's webform, construct the URL. The template detects FPO events by title, extracts the dissertation title from `field_ps_events_subtitle`, the date and location from their respective fields, and parses committee members from the body field (`field_ps_body`). The body field returns a render array, so `|render` is required before `|striptags`.

```twig
{# 1. Get the node title and check for FPO #}
{% set title = webform_token('[webform_submission:source-entity:title]', webform_submission)|trim %}

{% if title matches '/^.{0,5}FPO/' %}
    {# 2. Dissertation title #}
    {% set dissertation = webform_token('[webform_submission:source-entity:field_ps_events_subtitle]', webform_submission)|trim %}

    {# 3. Date and location #}
    {% set date = webform_token('[webform_submission:source-entity:field_ps_events_date:value]', webform_submission)|trim %}
    {% set location = webform_token('[webform_submission:source-entity:field_ps_events_location_name]', webform_submission)|trim %}

    {# 4. Extract committee from body field — render first to flatten render array #}
    {% set body = webform_token('[webform_submission:source-entity:field_ps_body]', webform_submission)|render|striptags|trim %}
    {% set committee = '' %}
    {% if body and 'members are ' in body %}
        {% set raw = body|split('members are ')|last|trim|trim('.')|trim %}
        {% set committee = raw|replace({'Professors ': '', 'Professor ': ''}) %}
    {% endif %}

    <a class="cke-button-secondary" href="https://pu-orfe.github.io/fpo-flyers/view.html?candidate={{ title|url_encode }}&title={{ dissertation|url_encode }}&date={{ date|url_encode }}&location={{ location|url_encode }}&committee={{ committee|url_encode }}&bg=tan">FPO Flyer</a>
{% else %}
    {# <p>Debug: Title detected as "{{ title }}"</p> #}
{% endif %}
```

**Field reference:**

| Token | Drupal field | Notes |
|-------|-------------|-------|
| `title` | Node title | Expected format: `"FPO, Candidate Name"` |
| `field_ps_events_subtitle` | Subtitle | Dissertation title |
| `field_ps_events_date:value` | Event date | ISO 8601; `:value` suffix returns raw string |
| `field_ps_events_location_name` | Location | e.g., `125 - Sherrerd Hall` |
| `field_ps_body` | Body (description) | Render array — must use `\|render\|striptags`; committee names parsed from text after "members are" |

## CI/CD

The GitHub Actions workflow runs every 30 minutes and can be triggered manually. When the feed changes, it generates PDFs and deploys them to GitHub Pages.

Trigger manually with force regeneration:
**Actions → Generate FPO Flyers → Run workflow → check "Force regeneration"**
