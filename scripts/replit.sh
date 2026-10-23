#!/bin/sh
# Keep dependency tooling separate from the application environment managed by uv.
set -eu
cd "$(dirname "$0")/.."
# Production starts only from the built environment: no package downloads on boot.
if [ "${1:-dev}" = start ]; then
  echo '[Noka] Checking built runtime and frontend'
  if [ ! -x .venv/bin/python ] || [ ! -f frontend/dist/index.html ]; then
    echo '[Noka] Build artifacts missing. Run the deployment build command first.' >&2
    exit 1
  fi
  export PYTHONUNBUFFERED=1
  echo '[Noka] Applying database migrations'
  .venv/bin/python -m alembic upgrade head
  echo '[Noka] Starting HTTP server'
  exec .venv/bin/python scripts/start.py
fi

echo '[Noka] Preparing build tools'
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
  dev)
    corepack pnpm install --frozen-lockfile
    corepack pnpm build
    "$UV" sync --frozen --python python3
    "$UV" run alembic upgrade head
    exec "$UV" run python scripts/start.py
    ;;
  *) echo 'Usage: sh scripts/replit.sh [dev|build|start]' >&2; exit 2 ;;
esac
