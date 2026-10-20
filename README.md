# Noka

Navigate tomorrow’s work, today. Phase 2 adds a real, attributed role/skill knowledge graph, US sector history, official UN goals/targets and provenance APIs to the light-themed React/FastAPI shell. See [product specification](docs/PRODUCT_SPEC.md), [source register](docs/DATA_SOURCES.md) and [original playbook](docs/IMPLEMENTATION_PLAYBOOK.md).

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
pnpm typecheck
pnpm build
pnpm test
uv run pytest
```

Build first: API integration tests verify that the actual bundle exists and is served at `/`, `/profile`, `/forecast`, `/design-preview` and `/profile/intake`. `/api/health` is liveness; `/api/ready` checks database connectivity, migration revision `0002` and (in production) the frontend bundle. Missing dependencies return 503 with a consistent error envelope. Health checks do not require AI/search keys. No API routes in this phase use those services.

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

1. The local repository has `origin` configured at `https://github.com/Rohansarav/noka-ai.git`. Push the desired reviewed commit to that repository (`git push -u origin main`) before importing into Replit. Verify `git remote -v` first if working in a copy of this project.
2. In Replit, import that GitHub repository and use the checked-in `.replit` configuration and `replit.nix` (uv). Ensure Node 22, Python 3.11+ and Corepack/pnpm are available in the Replit environment. The build installs locked dependencies and builds the frontend; startup migrates the database and runs FastAPI. Configuration follows the [official Replit configuration reference](https://docs.replit.com/features/project-setup/configuration), including `cloudrun` as the Autoscale deployment target. Hosting execution still requires verification on Replit.
3. Create a Replit PostgreSQL database and set `DATABASE_URL` in **deployment secrets**, along with `ENVIRONMENT=production`. `PORT=8000` is configured; the app respects a host override. Optional future secrets: `OPENAI_API_KEY`, `OPENAI_MODEL`, `TAVILY_API_KEY`, `INGESTION_SECRET`. Never prefix secrets with `VITE_`, paste them into source, or commit `.env`. AI/search keys are not needed for Phase 0.
4. Use Replit **Publish** / Autoscale web deployment. Review build logs, migration success and port mapping (8000 → 80). Workspace preview is not a published deployment.
5. Open the resulting public `https://<deployment>.replit.app` URL independently of the workspace. Verify `/`, `/profile`, `/forecast`, `/api/health` and `/api/ready`; both API probes should return HTTP 200. Refresh each deep link directly. Test a narrow viewport. Save the exact public URL and verification time in `docs/PHASE_0_REPORT.md`.

This repository has not been publicly deployed unless the phase report supplies a verified public URL. Replit service availability and account authorization must be established separately. SQLite must not be used as persistent production storage on Autoscale.

## Scope and privacy

All eight module routes exist. `/datasets` and `/signals` show data provenance and dated historical rows; `/matches` is a public role catalogue, explicitly distinct from personalized matching; `/sdgs` shows all imported goals and targets. `/design-preview` remains the labelled component gallery. `/profile/intake` is a non-collecting preview with disabled upload/manual-entry controls. The homepage separates successful historical imports from disconnected live AI feeds and API health. No resume upload, profile persistence, live search-feed ingestion, trained forecast, scenario simulator or learning progress exists yet. No resume data is collected. Access logs are disabled; API errors log only error classes. Source attribution and restrictions are in `docs/DATA_SOURCES.md`.

## Phase 2: import verified public evidence

Set `DATABASE_URL` in `.env` to your PostgreSQL connection string (never paste it into chat or commit it). SQLite remains a local fallback; it does **not** meet the PostgreSQL acceptance requirement. `uv sync --frozen` installs the PostgreSQL driver. No new AI/search key is required.

```sh
uv run alembic upgrade head
uv run python scripts/import_data.py --dry-run
uv run python scripts/import_data.py --offline
uv run python scripts/start.py
```

The first import command downloads to ignored `data/raw/` and validates without any database writes. The second verifies those cached files' manifest and performs an atomic, idempotent upsert into the database configured at process startup. To download and import in one step, omit `--dry-run` and `--offline`. Source download retries are bounded. WEF is imported as manually reviewed source-controlled reference records with separately verified PDF provenance; its copyrighted full PDF is not redistributed or downloaded on every import. Imports are explicit CLI actions; no public API starts a refresh.

For a clearly labelled offline real-row test subset:

```sh
uv run python scripts/import_data.py --directory data/fixtures --offline --dry-run
```

Never use the three-day fixture subset as full production history. Its manifest and API notes identify the original files and the subset transformation. Full source schema, licensing/terms, checksums, original-date availability, crosswalk judgement and revision limitations: [DATA_SOURCES.md](docs/DATA_SOURCES.md). Project-owner human review of the curation is recorded in [CURATION_REVIEW.md](docs/CURATION_REVIEW.md) and `data/curation/catalogue.json`.

Public read-only endpoints:

- `GET /api/roles`, `GET /api/roles/{id}` (O*NET-SOC codes, e.g. `15-1252.00`)
- `GET /api/skills`
- `GET /api/datasets/summary`
- `GET /api/demand/history?sector=Software%20Development` (optional ISO `start`/`end` dates)
- `GET /api/sdgs`

Verify `/api/datasets/summary` reports `database: postgresql`, `job_demand_observations: 114821`, `sdgs: 17`, `sdg_targets: 169`, and `2020-02-01`..`2026-10-09` for the pinned source version. Run `uv run python scripts/verify_evidence.py --require-postgres` for a read-only acceptance probe (it fails explicitly on SQLite or incomplete data). Run the import twice to verify counts remain unchanged; import audit rows intentionally accumulate. `/api/roles` never labels an individual role statistically forecastable. See `/docs` for the generated strict response schemas. Replit still needs a verified public deployment; local success is not public publishing.

## Visual system and QA

The light-only colour, gradient, radius, motion and chart tokens live in `frontend/src/style.css`. Primary blue is retained as a brand token; action backgrounds use a darker blue so white button labels meet contrast requirements. Chart samples include names and distinct line patterns. Subtle motion is disabled under `prefers-reduced-motion: reduce`.

At 375px, 768px and 1440px viewport widths, inspect `/`, `/design-preview`, `/profile`, and `/profile/intake`: check horizontal overflow, card stacking, navigation, focus rings, toast dismissal and legibility. Mobile navigation should focus its first link when opened, close on Escape, and restore toggle focus. Route changes focus main content. Component samples must never appear as real profile or market results. See `docs/PHASE_1_REPORT.md` for completed checks and any outstanding visual verification.
