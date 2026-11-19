# Exact tag plus multi-arch digest; Dependabot proposes updates.
FROM python:3.12.16-slim-trixie@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

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
