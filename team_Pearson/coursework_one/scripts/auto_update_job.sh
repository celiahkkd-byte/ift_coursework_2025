#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COURSEWORK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$COURSEWORK_DIR/.." && pwd)"

POETRY_BIN="${POETRY_BIN:-/Users/celiawong/.local/bin/poetry}"

cd "$REPO_ROOT"
# Ensure required infra is available before pipeline update.
docker compose up -d postgres_db mongo_db miniocw

cd "$COURSEWORK_DIR"
"$POETRY_BIN" run python scripts/run_scheduled_pipeline.py --only daily
