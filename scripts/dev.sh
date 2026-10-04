#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
pnpm --dir frontend install --frozen-lockfile=false
pnpm --dir frontend build
exec uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-3000}" --reload
