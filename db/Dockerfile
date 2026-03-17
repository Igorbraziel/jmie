# ══════════════════════════════════════════════════════════════════════
# db/Dockerfile — Database migrations and seeds image
# ══════════════════════════════════════════════════════════════════════
#
# This image runs Alembic migrations and seed scripts.
# It is NOT the PostgreSQL database itself — that uses the official
# postgres:15 image defined in docker-compose.yml.
#
# Designed as a one-shot container:
#   docker compose run --rm db-migrations
#
# The container runs init.sh, which:
#   1. Applies all pending Alembic migrations
#   2. Seeds the sources table
#   3. Exits cleanly
#
# Build context: repo root (.)
# Why root context? The Dockerfile needs to COPY workspace pyproject.toml
# files from scraper/, nlp/, api/, dags/ for uv workspace resolution.
# ══════════════════════════════════════════════════════════════════════

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
# curl: required by uv installer
# ca-certificates: required for HTTPS connections
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# ── Copy workspace manifests ──────────────────────────────────────────────────
# All workspace members must be present for uv to resolve the lockfile.
# The actual source code is copied separately below for better layer caching.
COPY pyproject.toml uv.lock ./
COPY db/pyproject.toml ./db/
COPY api/pyproject.toml ./api/
COPY scraper/pyproject.toml ./scraper/
COPY nlp/pyproject.toml ./nlp/
COPY dags/pyproject.toml ./dags/

# ── Install dependencies ──────────────────────────────────────────────────────
# --no-install-workspace: install dependencies only, not the workspace packages
#   themselves (avoids needing source code present at install time)
# --no-dev: exclude dev tools (pytest, ruff) from the runtime image
# --frozen: exact lockfile versions — reproducible builds
RUN uv venv /opt/venv \
    && uv sync \
        --frozen \
        --no-dev \
        --no-install-workspace \
        --python /opt/venv/bin/python

ENV PATH="/opt/venv/bin:$PATH"

# ── Copy application source ───────────────────────────────────────────────────
# Only the db/ directory — this image has no knowledge of api/, scraper/, etc.
COPY db/ ./db/
COPY alembic.ini ./alembic.ini

# Make the init script executable
RUN chmod +x db/scripts/init.sh

# Run as non-root for security
RUN groupadd -r dbuser && useradd -r -g dbuser dbuser
RUN chown -R dbuser:dbuser /app /opt/venv
USER dbuser

# Default command: run migrations + seeds
CMD ["bash", "db/scripts/init.sh"]