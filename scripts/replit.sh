#!/bin/sh
# Keep dependency tooling separate from the application environment managed by uv.
set -eu
cd "$(dirname "$0")/.."
python3 -m venv .replit-tools
.replit-tools/bin/python -m pip install --disable-pip-version-check 'uv==0.13.1'
UV="$PWD/.replit-tools/bin/uv"
export UV_PYTHON_DOWNLOADS=never

case "${1:-dev}" in
  build)
    corepack pnpm install --frozen-lockfile
    corepack pnpm build
    "$UV" sync --frozen --no-dev --python python3
    ;;
  start)
    "$UV" run --no-dev alembic upgrade head
    exec "$UV" run --no-dev python scripts/start.py
    ;;
  dev)
    corepack pnpm install --frozen-lockfile
    corepack pnpm build
    "$UV" sync --frozen --python python3
    "$UV" run alembic upgrade head
    exec "$UV" run python scripts/start.py
    ;;
  *) echo 'Usage: sh scripts/replit.sh [dev|build|start]' >&2; exit 2 ;;
esac
