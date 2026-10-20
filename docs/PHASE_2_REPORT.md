# Phase 2 — Knowledge graph, real datasets and evidence

20 October 2026 · Asia/Kuala_Lumpur. Implemented Phase 2 only.

## Acceptance result

**Verified in PostgreSQL**, not just the local SQLite fallback. Migration `0002` applied, real sources imported successfully twice, and a read-only acceptance probe confirmed unchanged persisted counts and date range. Local app at http://localhost:8000 now reads PostgreSQL. No public Replit publishing is claimed.

| Persisted evidence | Verified count |
|---|---:|
| Indeed US total-posting observations | 114,821 |
| US occupational sectors | 47 |
| Curated O*NET roles | 25 |
| Canonical O*NET skills | 35 |
| Role–skill importance mappings | 875 |
| Official UN goals | 17 |
| Official UN targets | 169 |
| Human-reviewed role/skill–SDG links | 7 |
| Attributed WEF qualitative context records | 4 |
| Source records | 6 |

Every sector has 2,443 daily observations, **2020-02-01 through 2026-10-09**. New-posting rows remain separate and are not imported into the total-posting series. No Malaysian history, individual-role/skill statistical forecasts, fabricated metrics or model results are included.

Machine-readable PostgreSQL verification: [postgresql-verification.json](qa/phase2/postgresql-verification.json). The probe records migration, counts, two successful full imports, date range, source versions/checksums and check time without connection credentials.

## What changed

- SQLAlchemy evidence graph and frozen Alembic migration, PostgreSQL/SQLite-native upserts and SQLite foreign-key enforcement.
- Pinned Indeed download, exact-schema validation, missing/non-finite value rejection, duplicate/conflict handling, deterministic sorting, US-only geography validation and traced source attribution.
- O*NET 31.0 occupation and essential/transferable skill CSV import, original IM 1–5 importance scale; 25 curated occupations, documented sector judgement and two uncovered occupations. No individual role is labelled statistically forecastable.
- Official UN API import of all 17 goals and 169 targets. Every goal is visible even without role links.
- Project owner explicitly reviewed and approved the crosswalk, seven SDG rationales and four WEF summaries in this chat. Review metadata is bound to a content fingerprint; later edits cannot silently inherit approval. See [curation review](CURATION_REVIEW.md).
- Atomic imports with last-successful preservation, separate failure audits, bounded download retries, safe progress logs, dry-run and checksum-verified offline directory import.
- Strict Pydantic API contracts and aligned TypeScript interfaces for all requested endpoints.
- Data provenance/dated history at `/datasets` and `/signals`, searchable role/skill catalogue at `/matches`, official-goal explorer at `/sdgs`, and a homepage status tile which distinguishes historical imports from disconnected live AI feeds.
- Real-row source fixtures and derived API test responses, with explicit original URL/checksum/retrieval/subset transformations. No fictitious fallback observations.

## Files changed

- `backend/app/models.py`, `schemas.py`, `evidence_api.py`; updates to `main.py` and `database.py`.
- `backend/app/ingestion/{__init__,sources,parsers,runner}.py`.
- `backend/migrations/versions/0002_evidence.py`, migration environment update.
- `scripts/import_data.py`, `scripts/verify_evidence.py`.
- `backend/tests/test_ingestion.py`, readiness test revision in `backend/tests/test_api.py`.
- `frontend/src/evidence-api.ts`, `EvidencePages.tsx`, `EvidencePages.test.tsx`; updates to `App.tsx`, `App.test.tsx`, `style.css`.
- `data/curation/catalogue.json`, `wef_source.json`; attributed small subsets in `data/fixtures/` and fixture manifest/README/API derivative.
- `docs/DATA_SOURCES.md`, `docs/CURATION_REVIEW.md`, this report, `docs/qa/phase2/` screenshots and verification JSON.
- `README.md`, `AGENTS.md`, `.gitignore`, `.gitattributes` (preserve exact fixture bytes/checksums across platforms).

Raw downloads remain ignored in `data/raw/`. The user's private PostgreSQL configuration stays in ignored `.env`; the tracked example retains placeholders. No new dependencies or dependency-lock changes were needed.

## Commands and verification

Run from repository root. On this machine, `pnpm` is `C:\Users\Rohan\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd`; Python commands used `.venv\Scripts\python.exe`.

```sh
uv run alembic upgrade head
uv run python scripts/import_data.py --dry-run
uv run python scripts/import_data.py --offline --dry-run
uv run python scripts/import_data.py --directory data/fixtures --offline --dry-run
uv run python scripts/import_data.py --offline
uv run python scripts/import_data.py --offline
uv run python scripts/verify_evidence.py --require-postgres
uv run pytest -q
pnpm typecheck
pnpm build
pnpm test
uv run python scripts/start.py
git diff --check
```

Actual Python invocation used `.venv\Scripts\python.exe`; PostgreSQL migration was executed via `alembic.command.upgrade(Config('alembic.ini'), 'head')` in that interpreter, with sanitized failure handling. The local SQLite fallback was migrated and exercised before PostgreSQL configuration became available. PostgreSQL was initially empty, then migrated and loaded twice successfully; audit entries intentionally accumulate while evidence counts remain stable.

- **Backend: 28 tests passed.** Coverage: real-row parsing, original metadata, strict source schemas, missing/invalid values, sorted dates, duplicates/conflicts, rejection of substituted geography, all official goals/targets, invalid crosswalk, content-bound human review, dry-run no writes, idempotence, source FKs/UTC timestamps, failed-import preservation, API schemas and existing health/readiness/SPA behavior.
- **Frontend: 42 tests passed**, including retained visual-token contrast tests, navigation, honest intake/status, real-fixture provenance dates/geography/source links, historical rows/retry after transient failure, searchable skill details, all 17 goals and reviewed target relevance, and failed-latest-import handling.
- **Typecheck and production build passed.** No changes to the one-service Replit serving arrangement.
- **Live PostgreSQL API probes: HTTP 200** for `/api/health`, `/api/ready`, `/api/roles`, `/api/roles/15-1252.00`, `/api/skills`, `/api/datasets/summary`, `/api/demand/history?sector=Software%20Development`, and `/api/sdgs`. Summary reports `database=postgresql`; software history returns 2,443 sorted dates; all 25 roles report `individual_statistically_forecastable=false`.
- **Browser QA:** `/datasets`, `/matches`, `/sdgs` at 375px, 768px and 1440px: nine route/viewport combinations, no document-level horizontal overflow, one H1 per page. Verified historical rows with dates/source links, software-developer skill ratings, expansion of official Goal 4 targets and reviewed rationales, and the final PostgreSQL storage banner. Viewport overrides reset afterward.
- [Responsive measurements](qa/phase2/responsive-results.json), [mobile goals](qa/phase2/sdgs-375.png), [final PostgreSQL provenance screenshot](qa/phase2/postgresql-provenance-1440.png).
- One existing upstream Starlette/httpx test-client deprecation warning remains; it did not fail tests. Physical-device and screen-reader testing were not performed.

## Source access and limitations

Indeed's actual current repository path, columns, daily frequency, licence and file hash were verified. O*NET 31.0 download links, schemas and CC BY 4.0 attribution requirements were verified. The UN official API returned all targets; target 4.4 was cross-checked on its official goal page. Full source detail and exact URLs are in [DATA_SOURCES.md](DATA_SOURCES.md).

Direct automated WEF webpage retrieval was restricted; the official report PDF was successfully retrieved, verified and hashed instead. Only short, reviewed, attributed summaries and PDF provenance are retained; the copyrighted full PDF is not redistributed. The general UN terms page also restricted direct retrieval, so no broader open licence/redistribution permission is asserted for official UN reference text. These restrictions did not block retrieval of the actual requested datasets.

Historical snapshots may contain revisions and do not establish a time-valid forecast backtest. Sector proxies are not individual occupation/skill time series. WEF global 2025–2030 context is separate from US historical data and future four-week ML forecasts. No trained forecast, profile intake, live AI/search feed or roadmap persistence was implemented.

## Deployment, blockers and commit

- Local FastAPI service is running on port 8000 with the built frontend and verified PostgreSQL evidence.
- No remaining Phase 2 implementation/data-access blocker. Replit public deployment remains unverified and was not performed in this phase. The configured GitHub remote is preserved; changes have not been pushed by this work.
- Commit message: `feat: ingest verified public evidence and expose the Noka knowledge graph`.
- Stopped after Phase 2.
