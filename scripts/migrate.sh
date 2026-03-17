#!/usr/bin/env bash
set -euo pipefail

echo "Running Alembic migrations..."
uv run alembic upgrade head

echo "Seeding sources table..."
uv run python db/seeds/01_seed_sources.py

echo "Init complete."