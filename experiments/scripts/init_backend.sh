#!/usr/bin/env bash
set -euo pipefail

# Initialize backend with test data for experiments
# This script is a wrapper around init_backend.py

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
EXPERIMENTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$EXPERIMENTS_DIR/.." && pwd)"

# Use Python implementation
cd "$ROOT_DIR"
python3 "$SCRIPT_DIR/init_backend.py" "$@"
