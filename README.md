# Noka

Navigate tomorrow’s work, today. Phase 0: a light-themed React shell and a FastAPI service, with no fabricated product data. See [product specification](docs/PRODUCT_SPEC.md) and [original playbook](docs/IMPLEMENTATION_PLAYBOOK.md).

## Requirements

Node 22+, pnpm 11.25.0 (via Corepack), Python 3.11+, and uv. All commands below run from the repository root. Install pnpm using `corepack enable` and `corepack prepare pnpm@11.25.0 --activate`; install uv using its official installer or `python -m pip install uv`.

## Local development

Copy `.env.example` to `.env` (PowerShell: `Copy-Item .env.example .env`; shell: `cp .env.example .env`). Leave `ENVIRONMENT=development`. SQLite is the local-only fallback.

```sh
pnpm install --frozen-lockfile
uv sync --frozen
uv run alembic upgrade head
pnpm dev
```

In a second terminal: `uv run python scripts/start.py`. Open http://localhost:5173. Vite proxies `/api` to port 8000. The API listens on `0.0.0.0`, reads `PORT` (default 8000), and allows only localhost/127.0.0.1:5173 CORS in development. To start both with one command after installing dependencies: `uv run python scripts/dev.py`.

## Verification

```sh
pnpm build
pnpm test
uv run pytest
```

Build first: API integration tests verify that the actual bundle exists and is served at `/`, `/profile`, and `/forecast`. `/api/health` is liveness; `/api/ready` checks database connectivity, migration revision and (in production) the frontend bundle. Missing dependencies return 503 with a consistent error envelope. Health checks do not require AI/search keys. No API routes in this phase use those services.

## Single-service production

```sh
pnpm install --frozen-lockfile
pnpm build
uv sync --frozen --no-dev
uv run --no-dev alembic upgrade head
uv run --no-dev python scripts/start.py
```

Set `ENVIRONMENT=production` and a PostgreSQL `DATABASE_URL` in the host environment. FastAPI serves both the compiled Vite assets and `/api/*`; SPA deep links are handled without returning HTML for missing API endpoints/assets. A database migration is performed before service startup. A failed migration blocks startup. No frontend server runs in production.

## GitHub and Replit Core publishing

1. Create one GitHub repository and push this local repository (`git remote add origin <your-repository-url>`, `git push -u origin main`). No GitHub remote is preconfigured.
2. In Replit, import that GitHub repository and use the checked-in `.replit` configuration and `replit.nix` (uv). Ensure Node 22, Python 3.11+ and Corepack/pnpm are available in the Replit environment. The build installs locked dependencies and builds the frontend; startup migrates the database and runs FastAPI. Configuration follows the [official Replit configuration reference](https://docs.replit.com/features/project-setup/configuration), including `cloudrun` as the Autoscale deployment target. Hosting execution still requires verification on Replit.
3. Create a Replit PostgreSQL database and set `DATABASE_URL` in **deployment secrets**, along with `ENVIRONMENT=production`. `PORT=8000` is configured; the app respects a host override. Optional future secrets: `OPENAI_API_KEY`, `OPENAI_MODEL`, `TAVILY_API_KEY`, `INGESTION_SECRET`. Never prefix secrets with `VITE_`, paste them into source, or commit `.env`. AI/search keys are not needed for Phase 0.
4. Use Replit **Publish** / Autoscale web deployment. Review build logs, migration success and port mapping (8000 → 80). Workspace preview is not a published deployment.
5. Open the resulting public `https://<deployment>.replit.app` URL independently of the workspace. Verify `/`, `/profile`, `/forecast`, `/api/health` and `/api/ready`; both API probes should return HTTP 200. Refresh each deep link directly. Test a narrow viewport. Save the exact public URL and verification time in `docs/PHASE_0_REPORT.md`.

This repository has not been publicly deployed unless the phase report supplies a verified public URL. Replit service availability and account authorization must be established separately. SQLite must not be used as persistent production storage on Autoscale.

## Scope and privacy

All eight routes exist; feature screens explain what is pending. No upload, session/profile persistence, feed ingestion, trained forecast, scenario simulator or learning progress exists yet. A working seeded journey belongs to subsequent phases. No resume data is collected. Access logs are disabled; unhandled API errors log only an exception class. No server secrets are exposed through an API. Source attribution and planned data restrictions are in `docs/DATA_SOURCES.md`.
