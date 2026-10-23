# Phase 3.5B: reviewable pathway updates

Implemented 2026-10-23. Production publishing remains on hold. No Phase 3.5C work.

## Delivered

Saved job-grounded projects now offer **Check reviewed evidence** and **Try synthetic replay**. Current approved occupation-change claims feed a bounded task interpretation and a proposed additional milestone. Users see sources, geography, occupation mapping scope, conditions, and before/after wording before accepting or dismissing. Personal review does not approve public mappings.

Acceptance appends a milestone and snapshots the previous project. Existing milestone IDs, completion state and notes remain untouched. Decisions retain actor, timestamp, evidence snapshot and proposal. Previous decisions remain visible. Duplicate evidence checks return no change; pending proposals must be resolved before another check. Stale or changed evidence prevents acceptance. Provider failures and timeouts preserve the project.

Simulation is a deterministic, explicitly fictional workflow fixture. It uses the same proposal validation and decision flow, but cannot append to real projects, write public evidence or enter forecasting data. It does not measure prediction quality. It is a single replay scenario, not a generated labour-market dataset.

## Architecture and files

- `backend/app/pathway_evolution.py`: private check and decision endpoints, evidence selection, bounded background interpretation, simulation, audit snapshots.
- `backend/app/pathway_contracts.py`, `pathway_research.py`: response fields, persisted private JSON, timeout recovery and history.
- `backend/app/main.py`: route registration.
- `frontend/src/PathwayEvolution.tsx`, `PathwayResearch.tsx`, `pathway-research-api.ts`, `pathway-research.css`: responsive review panel, actual pending-state animation, polling, decisions and history.
- `backend/tests/test_pathway_evolution.py`, `frontend/src/PathwayEvolution.test.tsx`: behavior tests.
- `scripts/verify_pathway_browser.cjs`: disposable desktop/mobile visual fixture; no actual human review or provider calls.

Uses existing PathwayResearch private JSON storage; no new migration. Public evidence remains in the existing reviewed market evidence store. Search receives no profile/resume data in this flow. No GPU work.

## Verification

- `.venv/Scripts/python.exe -m pytest backend/tests -q`: 166 passed before two extra focused tests were added.
- `.venv/Scripts/python.exe -m pytest backend/tests/test_pathway_evolution.py backend/tests/test_pathway_research.py -q`: 19 passed including the two added tests, after history changes.
- `node node_modules/vitest/vitest.mjs run --config frontend/vite.config.ts`: 133 passed across 19 files.
- `pnpm build`: TypeScript and production build passed. Existing bundle-size warning remains.
- `node scripts/verify_pathway_browser.cjs --proposal-fixture` with bundled Playwright NODE_PATH: desktop/mobile render passed; no horizontal overflow or browser errors; disposable profile deleted. Screenshots in `docs/qa/pathway-research/*evolution-fixture.png`.
- Local `/api/health` reports ok and `/api/ready` reports ready.

Provider behavior is mocked in backend tests. No new live OpenAI interpretation was claimed or editorial mapping approved by automation. Existing test warnings: Starlette/httpx deprecation and jsdom scrollTo.

## Boundaries

This is an on-demand vertical slice, not a durable scheduled monitor. Scout/editorial ingestion remains separate; only its approved current occupation-change evidence can reach real update proposals. Background tasks are process-local; an interrupted check expires and can be retried. Claims too broad or irrelevant can yield no change. No new role catalogue, specialty taxonomy, SDG mapping, or job growth/decline forecast is manufactured. The fixture demonstrates the workflow even when approved evidence is absent.

No deployment. No commit created: the workspace includes a substantial previously staged change set and earlier uncommitted pathway implementation; these were preserved without bundling unrelated changes.
