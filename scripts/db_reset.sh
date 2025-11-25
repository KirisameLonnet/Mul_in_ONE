#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
POSTGRES_DATA="${POSTGRES_DATA:-$ROOT_DIR/.postgresql/data}"

echo "⚠️  WARNING: This will DELETE ALL DATA in PostgreSQL!"
echo "Data directory: $POSTGRES_DATA"
echo ""
read -p "Are you sure you want to reset? Type 'yes' to confirm: " -r
echo
if [[ ! $REPLY =~ ^yes$ ]]; then
  echo "Aborting reset."
  exit 1
fi

echo "Resetting PostgreSQL cluster at $POSTGRES_DATA"
if [ -d "$POSTGRES_DATA" ]; then
  # Stop the server if it's running before removing the directory
  if pg_ctl -D "$POSTGRES_DATA" status >/dev/null 2>&1; then
    echo "Stopping running PostgreSQL server..."
    pg_ctl -D "$POSTGRES_DATA" stop -m fast
  fi
  
  # Create a backup before deleting (optional but recommended)
  BACKUP_DIR="$ROOT_DIR/.postgresql/backups"
  mkdir -p "$BACKUP_DIR"
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  BACKUP_NAME="backup_before_reset_$TIMESTAMP.tar.gz"
  echo "Creating backup: $BACKUP_DIR/$BACKUP_NAME"
  tar -czf "$BACKUP_DIR/$BACKUP_NAME" -C "$ROOT_DIR/.postgresql" data 2>/dev/null || echo "Backup failed (data may be empty)"
  
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