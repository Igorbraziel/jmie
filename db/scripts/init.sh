#!/usr/bin/env bash
set -euo pipefail

# ── Validate environment ──────────────────────────────────────────────────────
if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL environment variable is not set."
    echo "Example: postgresql://jmie_user:password@postgres-app:5432/jmie_db"
    exit 1
fi

echo "════════════════════════════════════════════════════"
echo " JMIE Database Init"
echo " Time: $(date '+%Y-%m-%d %H:%M:%S UTC')"
echo "════════════════════════════════════════════════════"

# ── Step 1: Run Alembic migrations ───────────────────────────────────────────
echo ""
echo "--- Running Alembic migrations ---"

# `alembic upgrade head` applies all migrations that haven't run yet.
# If everything is already up to date, it exits cleanly with no changes.
alembic -c db/alembic.ini upgrade head

echo "Migrations complete."

# ── Step 2: Seed reference data ──────────────────────────────────────────────
echo ""
echo "--- Seeding reference data ---"

# Seed job board sources (idempotent — skips existing rows)
python db/seeds/01_seed_sources.py

echo "Seeding complete."

echo ""
echo "════════════════════════════════════════════════════"
echo " Database init complete ✅"
echo "════════════════════════════════════════════════════"