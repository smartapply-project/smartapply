#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
if command -v pnpm >/dev/null 2>&1; then
  pnpm --dir frontend install --frozen-lockfile=false
  pnpm --dir frontend build
fi
exec uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-3000}"
