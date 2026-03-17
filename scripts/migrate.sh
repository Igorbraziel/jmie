#!/usr/bin/env bash
set -euo pipefail

echo "Running Alembic migrations..."
alembic upgrade head

echo "Seeding sources table..."
python db/seeds/01_seed_sources.py

echo "Init complete."