# Job-grounded My Pathway — Phase 3.5B enhancement

Implemented 23 October 2026. This is the explicitly requested pathway enhancement, not the start of Phase 3.5C. Replit publishing remains on hold.

## Behavior

My Pathway reuses the saved career direction. A confirmed aspiration mapped to that direction preserves the user's specialty (for example AI Engineer within Software Developers). The UI offers **Research my target** and **Paste a description**. Entering or reloading the page reads saved work; it does not spend provider credits automatically.

The private research worker makes at most two Tavily searches, extracts at most six pages, and makes one structured AI analysis call. Search terms contain only the destination and market, never the resume, projects, constraints or skill inventory. Searches prioritize individual employer postings; LinkedIn and social-network scraping are excluded. Only extracted page text is used as requirement evidence, not search snippets. Duplicate extracted content is removed. The analysis rejects directories, unrelated and explicitly closed postings; vacancy availability remains unverified. Dates shown are retrieval dates, not invented publication dates.

Each requirement contains a source ID and a quotation checked against retrieved text. Proposed interpretations remain pending until the profile owner explicitly selects requirements and records their starting point. The review timestamp and reviewer role are persisted. The next bounded AI call uses those reviewed requirements, confirmed profile context and weekly commitment to propose one coherent project with 3–6 milestones. Every selected requirement must be covered by a milestone, with no invented requirement IDs. Suggested architecture and timeboxes remain planning assumptions.

Users review and select the project separately, then save milestone evidence and progress. Completion requires an evidence note of at least 20 non-whitespace characters and never upgrades proficiency. Research runs have separate stable milestone IDs. Refreshing research cannot overwrite earlier projects, and generated projects remain accessible beyond the most recent twenty research-only runs. Existing foundational exercises and notes remain available below the new research workspace.

## Interface

- Light mint/blue research hero with a compact visual explanation of the flow.
- Animated orbital loading graphic, with reduced-motion support.
- Server-reported Find jobs / Read sources / Connect requirements stages; no fake percentages or simulated thinking.
- Persisted activity journal, accessible status announcements and explicit timeout/provider errors.
- Source cards, verbatim requirement evidence, selection controls and self-reported starting points.
- Project brief, audience, scope, assumptions, requirement-linked milestones, learning topics and evidence capture.
- Responsive desktop/mobile layouts and keyboard focus indicators.

## Files

- `backend/app/pathway_contracts.py`: strict input/output and model proposal contracts.
- `backend/app/pathway_research.py`: private endpoints, Tavily discovery, grounding, review, project planning and progress.
- `backend/app/models.py` and `backend/migrations/versions/0009_pathway_research.py`: private revision storage, cascaded profile deletion.
- `backend/app/main.py`: router and migration readiness revision.
- `backend/app/profile_security.py`: bounded research request bodies.
- `frontend/src/PathwayResearch.tsx`, `pathway-research-api.ts`, `pathway-research.css`: research/project workspace and polling.
- `frontend/src/FuturePages.tsx`: integration above preserved foundational practice.
- `backend/tests/test_pathway_research.py`, `backend/tests/test_api.py`, `frontend/src/PathwayResearch.test.tsx`, `frontend/src/FuturePages.test.tsx`: new behavior and integration coverage.
- `scripts/verify_pathway_browser.cjs`: disposable desktop/mobile and optional live-provider QA; deletes its demo profile in `finally` and does not approve real researched requirements.

## Validation commands

Run from the repository root:

```powershell
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m pytest backend/tests -q
node node_modules/vitest/vitest.mjs run --config frontend/vite.config.ts
pnpm build
git diff --check
```

Browser QA uses an available Playwright module (`NODE_PATH` can point to the installed runtime packages) and Microsoft Edge:

```powershell
node scripts/verify_pathway_browser.cjs
# Optional bounded real Tavily/OpenAI requests:
node scripts/verify_pathway_browser.cjs --providers
```

The live check leaves actual requirements pending review and deletes the disposable profile. Automated fixture reviews in unit tests are not human approval of production mappings.

### Recorded results

- Full backend suite: **163 passed**. One existing Starlette/httpx deprecation warning.
- Full frontend suite: **131 passed across 18 files**. Existing jsdom `window.scrollTo` warnings are unrelated to this enhancement.
- Production frontend build and TypeScript check: passed.
- `git diff --check`: passed (Git reports its normal Windows line-ending notice).
- Migration 0009 and `/api/ready`: passed against the configured PostgreSQL database.
- Real Tavily + OpenAI research: discovered **14 candidate pages**, retrieved **4 source pages**, and grounded **12 requirements from 1 relevant posting**. Final state was **pending review**. Vacancy availability was not asserted. Evidence: `docs/qa/pathway-research/browser-report.json`.
- Desktop/mobile initial, loading and requirement-review views: inspected; no browser runtime errors or horizontal overflow in the successful live browser run. Its disposable profile was deleted.
- A separate real OpenAI call validated the project output contract and produced three milestones from an explicitly synthetic QA requirement. It was **not persisted or approved in the app**. Evidence: `docs/qa/pathway-research/planning-provider.json`.
- Desktop/mobile project proposal layouts were also inspected using that explicitly labelled synthetic proposal. No horizontal overflow or browser errors; the disposable profile was deleted. Evidence: `docs/qa/pathway-research/browser-fixture-report.json` and `*-project-fixture.png`. This visual check does not represent a human-approved production plan.

The project-provider check first timed out with a 50-second client deadline. The bounded provider deadline was raised to 85 seconds (with a 130-second planning lease), and the isolated check succeeded. No provider error bodies or credentials were logged.

## Deployment, operating limits and commit

Migration 0009 was applied to the configured PostgreSQL database. The local app serves its built frontend and API at `http://127.0.0.1:8000`; `/api/ready` confirmed a current migration and built frontend. No Replit publishing was performed.

Local restart command: `.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log`.

Provider keys remain server-side. Runs are bounded background tasks, not a durable queue; interrupted or expired runs fail visibly on the next read. There is a per-profile daily research quota, a concurrent-run guard and a global research concurrency bound. Five project-generation attempts are allowed per run. Source retrieval and provider availability can still fail; users can retry or paste a description. Job discovery is a small sample, not comprehensive market coverage. The first implementation generates one project proposal at a time and learning topics, not verified external course recommendations.

The workspace already contained a substantial staged change set before this request. Those staged changes were preserved. No commit was created, to avoid bundling unrelated existing work into this enhancement.

Tavily extraction timeout and partial-success behavior follow its [official Extract reference](https://docs.tavily.com/documentation/api-reference/endpoint/extract). The first live attempt exposed an extraction timeout; the second exposed poor search-result relevance. Both produced honest failure states; search ranking and extraction limits were corrected before the next check.
