# NOKA integrated build — verification and handoff

Verified locally on 21 October 2026. Repository: `C:\Users\Rohan\OneDrive - Asia Pacific University of Technology And Innovation (APU)\Desktop\Noka`. Branch: `feat/integrated-future`. The backend/ML checkpoint is `a2a2aea`; the final frontend/report checkpoint follows it on this branch.

## A. Executive summary

The existing React/FastAPI/PostgreSQL application now has My Future, a shared three-world dial, the interactive Career Universe, Intelligence Radar, persistent My Pathway, role-first My Impact, and a Model Lab backed by real training artifacts. The original skill matcher, graph, profile isolation and bounded agent execution remain in place.

World changes update scenario planning priorities, narratives and pathway previews across screens. They do not rewrite skill-fit scores or historical forecasts. Guide reuses the existing Matchmaker worker with additional read-only context tools. Scout has completed real Tavily research runs and persists its sources and activity. Seven existing approved SDG links remain approved; five new proposals await human review.

Observed verification: **89 backend tests passed, 72 frontend tests passed, production build passed**, real browser journeys exercised, real OpenAI Guide execution completed, and real Scout research completed. Local application: [Open NOKA](http://localhost:8010). Replit publication and remote scheduling are not activated; no public URL is claimed.

## B. Completed product map

| Screen | Actual functionality | Verification |
|---|---|---|
| Profile/intake | Labelled demo or existing intake; confirm skills and interests; session-owned profiles | Automated extraction/matcher/isolation tests; actual demo created through UI |
| My Future `/` | Personalized role summary, shared scenario, selected role, scenario comparisons and pathway preview | Automated and desktop/mobile browser checks |
| Career Universe `/universe` | Existing React Flow graph; five recommended roles; pan, zoom, fit, focus, details and expanded view; scenario annotations | Automated tests and actual pan/zoom/fit/keyboard-exit checks |
| Intelligence Radar `/signals` | Stored source-linked Scout/context feed, market filters, refresh activity, qualitative role/skill outlooks and uncertainty | Automated tests, real Tavily runs and browser filters/source inspection |
| My Pathway `/roadmap` | Role and hours controls, deterministic skill-gap milestones, private notes and progress; saved across reload/world changes | Automated tests, live HTTP acceptance and browser save/reload |
| My Impact `/sdgs` | Selected-role responsibilities and required skills linked to specific SDG targets; approved/pending distinction; all 17 goals explorer | Automated tests, PostgreSQL evidence audit and nurse browser journey |
| Guide panel | Contextual questions, recorded tools/events, saved question history/replay, explicit validated world-switch commands | Automated tests, real provider HTTP/browser execution, replay and world-switch checks |
| Model Lab `/model-lab`, `/forecast` | Actual training audit, dated sector forecasts, baseline comparisons, model selection policy and limitations | Artifact/API tests, actual CPU training and browser inspection |
| Existing evidence views | Roles, datasets, goals and prior profile routes remain available | Regression suite; not every legacy page received a separate new visual audit |

The visual treatment uses the existing NOKA brand with mint/cream surfaces, consistent navigation and responsive layouts. The supplied HTML informed the world-dial interaction; screenshots below are from the actual running application.

## C. ML results

### Data and evaluation

The actual PostgreSQL audit found **114,821 US Indeed daily seasonally adjusted index observations across 47 sectors**, dated 2020-02-01 through 2026-10-09. There were zero duplicate sector/date records and no missing whole weeks across the audited sectors. The graph store contains 25 occupations, 35 skills, 875 role-skill relations, 17 goals and 169 targets. These are different evidence populations; sector indices are not individual occupation forecasts.

Daily values become Monday–Sunday means; the incomplete final week is excluded. No missing-week interpolation is used. Features are the current index, lags 1/4/13/26/52 and trailing means/standard deviations over 4/13/26 weeks. Direct forecasts use 4-, 13- and 26-week horizons.

Each sector/horizon has five expanding-window selection origins and three later holdout origins, four weeks apart within each group. A horizon-length embargo ensures selection labels have matured before the first holdout origin. Training labels must mature on or before their origin. Feature invariance and embargo behavior are tested.

Actual CPU models: persistence, standardized Ridge (alpha 10), and XGBoost (80 trees, depth 3, learning rate .05, seed 42, two threads). Lowest selection-window MAE chooses each sector/horizon winner. A separate conservative deployment gate falls back to persistence for a whole horizon if the selected portfolio does not beat holdout baseline MAE.

### Observed pooled holdout MAE (index points)

Each horizon has 141 predictions: 47 sectors × three origins. They are **not 141 independent experiments**.

| Horizon | Persistence | Ridge | XGBoost | Selection winners before gate | Deployed policy |
|---|---:|---:|---:|---:|---|
| 4 weeks | 2.6744 | 2.7394 | 3.0699 | 2.7032 | 47 persistence |
| 13 weeks | 5.2166 | 5.1267 | 8.1633 | 5.3474 | 47 persistence |
| 26 weeks | 6.8482 | 9.1156 | 17.3096 | 6.2166 | 39 persistence, 7 Ridge, 1 XGBoost |

| Horizon | Selection portfolio RMSE | sMAPE | Directional accuracy |
|---|---:|---:|---:|
| 4 weeks | 3.8068 | 2.4350% | 16.3121% |
| 13 weeks | 7.6976 | 4.8567% | 44.6809% |
| 26 weeks | 8.4876 | 5.6534% | 12.7660% |

The 26-week selected portfolio improved MAE by about 9.22% in this limited window. This does not establish general future predictive skill. Ridge alone slightly beat pooled persistence at 13 weeks, but the selection portfolio failed that horizon's deployment gate. The product accurately exposes the resulting baseline fallback.

Artifacts: `ml/artifacts/evaluation.json` (590,961 bytes) and `ml/artifacts/models.joblib` (2,489,285 bytes). JSON includes audit, hyperparameters, individual backtests, forecasts and deployment policies. Input SHA-256: `ced59e9f0bf96ce8820cca07d2d8438fd6d03f9c0218858c769593592050e88c`. Generation: 2026-10-20T15:52:49Z. The last complete observation week is 4 October 2026; the longest forecast ends 4 April 2027. Scenarios never retrain or mutate these artifacts.

Limits: one revised historical vintage, only three overlapping holdout origins, dependent errors, US sector aggregates and no calibrated prediction intervals. Displayed ranges use the 80th percentile of five absolute selection errors and are descriptive. There are no numerical Malaysian occupation/skill demand, salary or job-count predictions. No GPU/RunPod training was used. Full methodology is in `ml/README.md`.

## D. Agent and evidence status

| Capability | Implemented logic | Automated verification | Real provider verification | User-facing integration |
|---|---|---|---|---|
| Scout | Bounded research, source extraction, URL deduplication, persistence, run events, PostgreSQL overlap lock and cooldown | Passed in backend suite | Two actual Tavily runs succeeded; latest 21 Oct 00:50–00:51 UTC (08:50–08:51 MY) | Radar shows sources and real run state; acceptance returned 27 feed items |
| Guide | Existing Matchmaker identity/API; ten bounded read-only tools; saved context/questions/execution references | Passed in backend/frontend suites | Real OpenAI execution completed with `get_future_context` and four lifecycle/tool events | Browser conversation, trace, history replay and explicit world switch verified |
| Impact | Deterministic role/skill/target evidence service and idempotent pending proposals | Tests and actual PostgreSQL audit passed with explicit pending-candidate flag | Not a separate external-model worker; no external approval execution claimed | Approved vs pending role-first trace and goal explorer verified |

Scout performs at most four searches, one extraction batch and three bounded publisher metadata requests. It never receives resumes or private profile content. Retrieved pages are evidence, not executable instructions. Dates are not inferred when unavailable. One retained DOSM source whose original query could not be recovered is marked `url_review_required`; its original-publication link is withheld in the UI. Source search snippets never automatically become verified demand assertions.

Three separately registered context records cover [Malaysia's proposed AI governance bill consultation](https://www.digital.gov.my/en-GB/siaran/Kementerian-Digital-Mulakan-Libat-Urus-Cadangan-Rang-Undang-Undang-Tadbir-Urus-Kecerdasan-Buatan-(AI)), [OpenAI's enterprise AI strategy](https://openai.com/index/next-phase-of-enterprise-ai/) and [TalentCorp MyCOL](https://www.talentcorp.com.my/mycol/). The government consultation is dated 10 July 2026 and is not presented as enacted legislation. The vendor statement is dated 8 April 2026 and is not Malaysian employment evidence. MyCOL's current collection is 2024/25; its overview does not validate invented occupation-specific forecasts.

Sixty stored role/skill outlooks include six evidence-supported role directions and six skill directions; 48 remain insufficient. Versioned mappings cite [WEF jobs outlook](https://www.weforum.org/publications/the-future-of-jobs-report-2025/2-jobs-outlook) and [skills outlook](https://www.weforum.org/publications/the-future-of-jobs-report-2025/3-skills-outlook). These global employer expectations are not local measured forecasts. Crosswalks remain pending human review. The system supports an emerging category, but current evidence does not justify assigning it.

Seven original human approvals remain intact. Five new unique pending candidates cover nursing/pharmacy → 3.8, sustainability → 12.6, security → 16.6 and industrial engineering → 9.4. Their existence does not mean a reviewer approved them.

Guide's worker API retains `matchmaker` for compatibility; Guide is not a second autonomous worker. Python renders authoritative scores and structured sections. Context includes saved scenario, role, hours, progress and recent questions; optional selected graph nodes are validated. Quotas, bounded tool loops, timeouts, cancellation, SSE events and ownership checks remain. World-switch commands accept only known explicit worlds. Notes and conversation references remain session-owned; last 30 questions are retained.

## E. Experience verification

The three worlds—Acceleration, Governed and Human-AI Collaboration—share persisted state. Backend previews drive immediate UI changes; saves roll back on failure. Planning ranks use the original top-five skill matches plus explicit scenario skill weights. Fit scores stay unchanged. Future Self copy is a deterministic, personalized narrative derived from the profile, selected role and scenario; it is not an unevaluated probabilistic prediction.

Actual browser checks used the labelled demo flow, confirmed suggestions and saved a role through the UI. No manually patched browser state was used. All three worlds changed narrative/priorities; Collaboration also changed lower role ordering. Refresh preserved the world.

The original graph panned from translate(73.2192px, 170.568px) to translate(153.219px, 210.568px), at unchanged scale .678082. Zoom, fit, role focus and expanded-dialog Escape exit worked. Annotations do not reset the graph layout.

The pathway slider was set by keyboard to 12 hours/week. Its first milestone changed from four weeks to two; saving, refresh and world switches preserved 12 hours, a completed Systems Analysis milestone and a private reflection note. Plans estimate effort from skill gaps (minimum four hours; otherwise rounded-up 24 × gap) and scenario ordering. They are sequential workloads, not verified course prerequisites or certifications. Fourteen skill-specific practice templates have a contextual fallback; no fabricated course URLs are shown.

The nurse impact journey exposed actual role responsibility, approved target 3.c, the Instructing → 4.4 connection and pending 3.8. A role with no approved links shows an honest empty state. Radar filters exposed Malaysian source context and the source-backed declining accountant outlook. Model Lab displayed the actual training audit and baseline fallbacks.

A real Guide browser question compared the selected role across worlds using saved context. It completed with four recorded events and displayed scenario/pathway context including 12 hours and completed progress. History reopened the execution. The explicit “Switch to Human-AI Collaboration” command changed the shared world without a model request.

Distinct disposable acceptance fixtures produced workforce top matches Data Scientists (30.1), Database Administrators (20.1), Software Developers (18.7), versus student Human Resources Specialists (7.9), Industrial Engineers (7.6), Data Scientists (7.2). Their pathway priorities differed. These are labelled test fixtures, not real people; profiles were cleaned up. Cross-session access returned denial.

Responsive checks: desktop 1440 × 900; mobile requested 375 × 812 (client width 360, scroll width 360); tablet requested 768 × 1024 (client/scroll width 753). No horizontal overflow was observed at those viewports. Mobile navigation opened with focus on its first link and closed after navigation. Loading/empty/provider-error handling has automated coverage; a failed lazy bundle now offers recovery instead of a blank workspace. Keyboard/focus and reduced-motion checks were exercised; no formal WCAG/screen-reader audit or physical-device test is claimed.

## F. Test report

Commands were run from the repository root. The final implementation passed:

| Command | Observed result |
|---|---|
| `uv run pytest -q` | 89 passed; one non-failing Starlette TestClient/httpx deprecation warning |
| `pnpm exec vitest run --config frontend/vite.config.ts --reporter=json --outputFile=../docs/qa/future-vitest.json` | 72 passed, zero failed, success true |
| `pnpm build` | TypeScript and Vite production build passed |
| `uv run alembic upgrade head` and revision inspection | PostgreSQL at 0005 head |
| `uv run python -m ml.train` | Actual CPU training/evaluation completed; checked-in artifacts produced |
| `uv run python scripts/verify_evidence.py --require-postgres --allow-pending-candidates` | Passed: 7 approved + 5 pending links, without approving candidates |
| `uv run python scripts/verify_future_live.py --provider` | Ready endpoint, 141 forecasts, isolation, scenario/progress and real OpenAI execution passed |
| Additional `verify('http://localhost:8010', False)` invocation | Distinct profiles and pathway priorities passed; saved `docs/qa/future-profiles.json` |
| `uv run python -m backend.app.scout` | Two real successful Tavily runs; persisted findings/run events |
| `uv run python -m backend.app.outlooks`, `uv run python -m scripts.register_context`, `uv run python -m scripts.propose_impact` | Real evidence initialization completed; no invented approval |

Saved sanitized machine-readable evidence: `docs/qa/future-live.json`, `future-profiles.json` and `future-vitest.json`. Earlier failures were repaired: forecast JSON non-finite metadata serialization, outdated navigation assertions, lazy-chunk failure recovery, and resource-sensitive default frontend timeouts. A targeted intake run passed, then the entire 72-test frontend suite passed with three workers and explicit timeouts. The strict legacy evidence command **does reject pending reviews**; the expanded audit uses its explicit flag and does not imply review completion.

The actual application received browser verification in addition to mocks and HTTP tests. No remote deployment, scheduled invocation, formal accessibility certification or exhaustive provider-outage browser exercise is claimed.

## G. Deployment report

The local single-service production build runs on port 8010. PostgreSQL migration 0005 persists future preferences, notes/progress, conversation references and intelligence records. Model artifacts are included in source. Production startup refuses SQLite. Readiness checks migration, database and built frontend.

Replit publication is on hold under the owner's prior instruction pending credits/authorization. No web deployment, scheduler or real public URL has been activated or verified. The existing `.replit`/single-service build path is retained. Required web secrets: `DATABASE_URL` (production PostgreSQL), `ENVIRONMENT=production`, `PUBLIC_ORIGIN` (actual HTTPS site origin), `OPENAI_API_KEY` for Guide and `TAVILY_API_KEY` for Scout. `OPENAI_MODEL` is configurable. Set `INGESTION_SECRET` only for protected ingestion operations. Secrets stay server-side; do not put them in frontend variables or commit `.env`.

For Scout use a **separate Scheduled deployment**, not a web-process timer. Build: `uv sync --frozen --no-dev`; run: `uv run --no-dev python -m backend.app.scout`; cron: `0 8 * * *`; timezone: `Asia/Kuala_Lumpur`; job timeout: 300 seconds. Use the same production PostgreSQL database and Tavily secret. Overlap locking and the persisted one-hour cooldown prevent duplicate refreshes. Enable job failure alerts. An abrupt crash is observable in scheduler logs, not mislabeled as success. This design follows [Replit's deployment documentation](https://docs.replit.com/features/publishing/deployment-types). Remote schedule timing still requires a real scheduled invocation after activation.

## H. Remaining issues and unverified requirements

- Owner review/credits block publication and remote scheduler activation; public URL and scheduled clock are unverified.
- Five SDG candidates and source-to-role/skill crosswalks await real human review. No review identity or approval has been fabricated.
- Forty-eight outlooks lack sufficient evidence; no evidence-supported emerging classification and no numerical Malaysian occupation/skill forecast exist.
- Some Scout publication dates remain unknown; one DOSM source URL needs review. Research findings do not automatically become verified trend directions.
- Three holdout origins and revised US data limit forecast claims. Scenario planning weights and pathway effort estimates are transparent assumptions, not empirically validated causal forecasts.
- Guide uses bounded structured responses; Impact is an evidence service rather than a separate LLM agent. Pathways do not assert external course completion, certifications or prerequisite validation.
- Accessibility and responsive checks are useful local evidence, not a formal audit, exhaustive device matrix or remote production acceptance.

No known failing final automated check remains. These limitations prevent a claim that every evidence and deployment requirement is fully complete.

## I. Final user handoff

The current demo is running at [localhost:8010](http://localhost:8010). The browser demo has a selected Software Developer role, 12 weekly learning hours, saved progress and the Human-AI Collaboration world. All demo identity labels are explicit.

To install and run from the source checkout in PowerShell:

```powershell
Set-Location 'C:\Users\Rohan\OneDrive - Asia Pacific University of Technology And Innovation (APU)\Desktop\Noka'
pnpm install --frozen-lockfile
uv sync --frozen
# Configure .env from .env.example with the intended PostgreSQL database and server keys.
uv run alembic upgrade head
pnpm build
$env:PORT = '8010'
uv run python scripts/start.py
```

For an empty database, after migrations import the real public data and initialize evidence:

```powershell
uv run python scripts/import_data.py
uv run python -m backend.app.outlooks
uv run python -m scripts.register_context
uv run python -m scripts.propose_impact
uv run python scripts/verify_evidence.py --require-postgres --allow-pending-candidates
uv run python -m backend.app.scout
```

Use `--offline` only if the complete verified public-source cache exists. Tiny test fixtures are not training data. The model artifact is included; retrain deliberately with `uv run python -m ml.train` when a new appropriate data vintage is available. Do not load an untrusted joblib file.

Minimum next owner actions: review the five target candidates and evidence crosswalks; authorize/fund Replit publication when ready; configure production secrets, migrate and publish the reviewed revision; verify the actual public `/api/ready`, sign-in/session ownership and full demo journey; create and verify the separate scheduled deployment. Deployment commands are documented in README and `docs/SCOUT_SCHEDULING.md`. The source archive excludes `.env`, database contents, node_modules and virtual environments.

## J. Actual application screenshots

The companion `Screenshot-Gallery.html` contains all 11 captures. They document the running product, not the reference HTML. Full-page captures may be tall.

### My Future — Acceleration

![My Future — Acceleration](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/screenshots/my-future-acceleration.jpg)

### World Dial — Governed

![World Dial — Governed](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/screenshots/my-future-governed.jpg)

### World Dial — Human-AI Collaboration

![World Dial — Human-AI Collaboration](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/screenshots/my-future-collaboration.jpg)

### Career Universe

![Career Universe](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/screenshots/career-universe.jpg)

### Intelligence Radar

![Intelligence Radar](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/screenshots/intelligence-radar.jpg)

### My Pathway

![My Pathway](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/screenshots/my-pathway.jpg)

### My Impact

![My Impact](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/screenshots/my-impact.jpg)

### Model Lab

![Model Lab](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/screenshots/model-lab.jpg)

### Mobile layout

![Mobile layout](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/screenshots/mobile-my-future.jpg)

### Tablet layout

![Tablet layout](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/screenshots/tablet-my-future.jpg)

### Guide activity

![Guide activity](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/screenshots/guide-activity.jpg)

