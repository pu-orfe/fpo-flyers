# Exact tags plus multi-arch digests; Dependabot proposes updates.
FROM ghcr.io/astral-sh/uv:0.13.10@sha256:a3ea1357342c1a4bf9a0c53a3deb1b55379aefa037338d8113d5771efa01774f AS uv
FROM python:3.12.16-slim-trixie@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

COPY --from=uv /uv /usr/local/bin/uv
# Install into a fixed venv using the image's Python; never download another interpreter.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

# WeasyPrint system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libcairo2 \
    libharfbuzz-subset0 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# Dependencies first, from uv.lock, so this layer caches across source edits.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev --no-cache

COPY src/ src/
RUN uv sync --locked --no-dev --no-editable --no-cache

ENTRYPOINT ["fpo-flyers"]
CMD ["--output-dir", "/app/output", "--verbose"]
