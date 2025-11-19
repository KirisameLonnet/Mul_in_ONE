#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
EXTERNAL_DIR="$ROOT_DIR/external"
TOOLKIT_DIR="$EXTERNAL_DIR/NeMo-Agent-Toolkit"

if [[ ! -d "$EXTERNAL_DIR" ]]; then
  mkdir -p "$EXTERNAL_DIR"
fi

if [[ ! -d "$TOOLKIT_DIR/.git" ]]; then
  echo "[bootstrap] cloning NeMo-Agent-Toolkit into $TOOLKIT_DIR"
  git clone https://github.com/NVIDIA/NeMo-Agent-Toolkit.git "$TOOLKIT_DIR"
else
  echo "[bootstrap] updating existing NeMo-Agent-Toolkit"
  git -C "$TOOLKIT_DIR" pull --ff-only
fi

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "[bootstrap] please activate your virtualenv (direnv/uv) before running this script" >&2
  exit 1
fi

uv pip install -e "$TOOLKIT_DIR"[langchain]
