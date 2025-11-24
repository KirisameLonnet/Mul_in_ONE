#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
POSTGRES_DATA="${POSTGRES_DATA:-$ROOT_DIR/.postgresql/data}"

echo "Resetting PostgreSQL cluster at $POSTGRES_DATA"
if [ -d "$POSTGRES_DATA" ]; then
  # Stop the server if it's running before removing the directory
  if pg_ctl -D "$POSTGRES_DATA" status >/dev/null 2>&1; then
    echo "Stopping running PostgreSQL server..."
    pg_ctl -D "$POSTGRES_DATA" stop -m fast
  fi
  echo "Removing existing data directory"
  rm -rf "$POSTGRES_DATA"
fi

mkdir -p "$POSTGRES_DATA"
echo "Initializing new PostgreSQL cluster..."
initdb -D "$POSTGRES_DATA" --auth=trust -U postgres

echo "Temporarily starting server to create database..."
pg_ctl -D "$POSTGRES_DATA" -l "$POSTGRES_DATA/postgres_reset.log" start

# Wait for server to be ready
for i in $(seq 1 5); do
  if pg_ctl -D "$POSTGRES_DATA" status >/dev/null 2>&1; then
    echo "Temporary server is ready."
    break
  fi
  sleep 1
done

echo "Creating application database 'mul_in_one'..."
createdb -U postgres mul_in_one

echo "Stopping temporary server..."
pg_ctl -D "$POSTGRES_DATA" stop -m fast

echo "PostgreSQL reset complete. Run './scripts/db_start.sh' to launch."