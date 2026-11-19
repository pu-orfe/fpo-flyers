# Exact tag plus multi-arch digest; Dependabot proposes updates.
FROM python:3.15.2-slim-trixie@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

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
# Dependencies first, from the hashed lockfile, so this layer caches across source edits.
COPY requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock

COPY pyproject.toml .
COPY src/ src/
# The lock already holds every dependency and the build backend: do not re-resolve.
RUN pip install --no-cache-dir --no-deps --no-build-isolation .

ENTRYPOINT ["fpo-flyers"]
CMD ["--output-dir", "/app/output", "--verbose"]
