#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
POSTGRES_DATA="${POSTGRES_DATA:-$ROOT_DIR/.postgresql/data}"
LOG_FILE="${POSTGRES_LOG:-$POSTGRES_DATA/postgres.log}"

if [ ! -d "$POSTGRES_DATA" ]; then
  echo "Postgres data directory '$POSTGRES_DATA' does not exist. Run 'scripts/db_reset.sh' first."
  exit 1
fi

if pg_ctl -D "$POSTGRES_DATA" status >/dev/null 2>&1; then
  echo "PostgreSQL already running for data directory $POSTGRES_DATA"
else
  pg_ctl -D "$POSTGRES_DATA" -l "$LOG_FILE" start
  echo "PostgreSQL started (log: $LOG_FILE)"
fi

echo "Waiting for PostgreSQL to be fully ready..."
for i in $(seq 1 10); do
  if pg_ctl -D "$POSTGRES_DATA" status >/dev/null 2>&1; then
    echo "PostgreSQL is ready."
    break
  fi
  echo "Still waiting ($i/10)..."
  sleep 1
done

if ! pg_ctl -D "$POSTGRES_DATA" status >/dev/null 2>&1; then
  echo "Error: PostgreSQL did not start in time."
  exit 1
fi

# Check if the database exists and create it if it doesn't.
# This makes the script resilient, not requiring a full reset for a new setup.
if ! psql -U postgres -lqt | cut -d \| -f 1 | grep -qw mul_in_one; then
  echo "Database 'mul_in_one' not found. Creating it..."
  createdb -U postgres mul_in_one
else
  echo "Database 'mul_in_one' already exists."
fi

echo "Running Alembic database migrations..."
(cd "$ROOT_DIR" && alembic upgrade head)
echo "Alembic migrations applied."