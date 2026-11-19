# FPO Flyers

Automated generation of Final Public Oral (FPO) examination flyers.

Fetches events from the department ICS feed, scrapes dissertation titles from event pages, and produces styled PDF flyers.

## Quick Start

```bash
# Requires uv: https://docs.astral.sh/uv/
uv sync --extra test --extra dev
source .venv/bin/activate
fpo-flyers --output-dir output --force --verbose
```

On macOS, install WeasyPrint's libraries with `brew install pango`. The project prefers the
Homebrew Python (`python-preference = "system"`), which finds them. If you use a uv-managed Python
instead (for example with `UV_MANAGED_PYTHON=1`), it does not search Homebrew's library directory,
so also run `export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib"`.

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

## Lint and type checks

```bash
ruff check src tests
ruff format --check src tests
mypy
```

## Updating dependencies

All Python dependencies, with hashes, are locked in `uv.lock`. Every install (the Dockerfiles, the
workflows, and local setup) runs `uv sync --locked`, which fails if the lock is out of date.

- **Routine updates:** Dependabot opens weekly PRs that update `uv.lock` (minor and patch updates
  grouped together, majors separately), plus the Docker images and GitHub Actions. CI must pass
  before they merge.
- **After editing dependencies in `pyproject.toml`:** run `uv lock` and commit `uv.lock`. CI
  runs `uv lock --check`.
- **Build backend:** `uv.lock` does not cover it, so `setuptools` and `setuptools-scm` are pinned
  in `[tool.uv] build-constraint-dependencies` in `pyproject.toml`. Update those by hand.
- **Python:** the project stays on 3.12. A new minor needs the Docker images and the workflows'
  `python-version` changed together, so Dependabot proposes only 3.12.x image updates.

## Branch protection

`main` only moves when the CI `lint` and `test` jobs pass. Force-pushes and deletion are
blocked. The rule is a repository ruleset defined in `.github/rulesets/main.json`. The GitHub
Actions app may bypass it, so `generate.yml` can still push feed-hash and keepalive commits.

After changing the JSON, or adding a CI job (a test requires every CI job to be listed), apply it
with an admin `gh` login:

```bash
scripts/apply-ruleset.sh --dry-run   # show what would be sent
scripts/apply-ruleset.sh             # create or update the ruleset
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

### Scheduled-workflow deactivation

GitHub disables scheduled workflows after 60 days without repository activity.
The feed can sit unchanged for an entire summer, producing no commits, so the
`check` job pushes a dated no-op commit to `.keepalive` once the last commit is
50 days old.

If the workflow is ever disabled anyway, the index page keeps serving the last
deployed `manifest.json` and reports "No flyers currently available" while
`view.html` still works, since it renders entirely from URL parameters. Confirm
with `gh workflow list --all` (look for `disabled_inactivity`) and re-enable with
`gh workflow enable generate.yml`.
