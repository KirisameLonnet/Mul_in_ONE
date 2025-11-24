#!/usr/bin/env bash
set -euo pipefail

# This script safely stops the local PostgreSQL server managed by pg_ctl.

SCRIPT_DIR="$(cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
POSTGRES_DATA="${POSTGRES_DATA:-$ROOT_DIR/.postgresql/data}"

# Check if the server is running.
if ! pg_ctl -D "$POSTGRES_DATA" status >/dev/null 2>&1; then
  echo "PostgreSQL is not running."
  exit 0
fi

echo "Stopping PostgreSQL server for data directory: $POSTGRES_DATA"
# The -m (mode) flag can be 'smart', 'fast', or 'immediate'.
# 'smart' waits for all clients to disconnect. 'fast' does not. 'fast' is suitable for development.
pg_ctl -D "$POSTGRES_DATA" stop -m fast

echo "PostgreSQL stopped."
