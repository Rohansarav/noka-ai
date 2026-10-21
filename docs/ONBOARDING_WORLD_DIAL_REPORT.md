# Onboarding and World Dial corrections

Implemented in the existing React / FastAPI / PostgreSQL application. No deployment was performed; Replit publication remains on the owner's hold.

## Root cause and state trace

The subtle response was caused by incomplete presentation, rather than a stale scenario cache. `useFuture` stores a shared scenario snapshot, immediately previews the server-provided `comparisons` and `worlds` for that scenario, then replaces the preview with the PUT response or rolls it back on failure. The API recomputes scenario emphasis, planning order, pathway priorities and Future Self from the selected scenario.

The career graph API intentionally contains factual confirmed skills, unchanged matcher scores, occupational requirements and reviewed SDG connections. It has no hypothetical scenario parameter. Previously, the graph received only small role annotations; the role detail panel received no future snapshot at all. This made correct shared-state changes look superficial. The graph remains factual; scenario presentation now receives the separate computed snapshot explicitly.

| Surface | Result |
| --- | --- |
| Shared future session | Same owned session, serialised mutations, immediate computed preview, persistence rollback retained |
| Scenario calculations | Original top-five matcher scores plus explicit O*NET-based scenario emphasis; formula unchanged |
| Career graph API | Factual API, ownership, sources, requirements and score values preserved |
| Career Universe | Smooth emphasis of displayed skills named in the selected role's computed priorities; role ordering uses actual planning order |
| Role details | Current scenario, assumption, relevant priorities and separate planning-index calculation |
| Future Self | Uses the selected world's existing computed story and priority skills |
| Intelligence Radar | Dial hidden; source records and research content preserved |
| My Pathway | Existing scenario adaptation, effort estimates, progress, notes, pace preview and explicit save preserved |
| My Impact / Model Lab | Dial hidden because these factual surfaces have no implemented scenario-dependent evidence change |

## Onboarding routes and completion

`/` and `/universe` wait for the owned profile before choosing a destination. Missing or unconfirmed profiles go to `/profile/intake`. Session errors show an honest retry state. Existing `confirmed=true` profiles, including those created before this change, enter the main experience immediately.

`/profile/intake` is a three-stage flow: About You, Your Skills, Your Direction. About You supports PDF/DOCX upload, local or optional OpenAI extraction, pasted experience, manual entry and an explicitly labelled demo. It captures status, current role or study field, years and country. Suggestions remain separate from reviewed skills and are never saved automatically. Users can select canonical alternatives, confirm, add, remove and change proficiency or years.

Direction captures career interests, goal, market (Malaysia by default) and 1–40 weekly learning hours. The interface explains the actual effects: skills determine fit, interests add the existing small preference adjustment, and hours set pathway pace. Background and free-text goals are saved context for the user; they are not additional scoring factors. Local market preference does not turn US O*NET data into Malaysian vacancy evidence.

Structured drafts save with a 700 ms debounce to an owned, CSRF-protected endpoint. Resume bytes, pasted text, unconfirmed suggestions and evidence excerpts are excluded. A single creation promise and a serial draft queue prevent competing saves. Completing onboarding requires a nonblank role/study field and at least three reviewed canonical skills. The final backend transaction saves reviewed fields, hours and a valid initial computed career direction together. Existing valid directions, progress and notes remain intact. The obvious **Edit Profile** link reopens the same flow with saved fields and manual mode, so uploading again is unnecessary. Edit prefill reads the current workspace hours, including for legacy profiles, rather than resetting a saved Roadmap pace to the onboarding default.

Migration `0006` adds a nullable onboarding JSON field; it does not rewrite existing profiles. Local PostgreSQL was upgraded successfully. Readiness requires `0006`.

## Genuine scenario-dependent presentation

The planning-lens panel shows relevant skills and a concise comparison with the preceding scenario: added and removed priorities, actual planning position, emphasis and unchanged fit. Unsupported emphasis gets an explicit explanation. An exact computed tie says that the evidence does not justify a change. No arbitrary node movement, ranking changes, new requirements or new SDG edges were introduced.

In the fresh manual browser journey, Software Developers retained position 1 and skill fit 18.3. Collaboration emphasised Active Listening, Critical Thinking and Active Learning (+1.76); Acceleration emphasised Technology Design, Programming and Systems Analysis (+1.88); Governed AI emphasised Judgment and Decision Making (+0.62). These are actual server-computed values for that test profile, not market observations. The graph transform remained exactly `translate(-467.5px, 115.8px) scale(0.8)` through a scenario switch. Selection remained Software Developers.

No complete priority/emphasis tie occurred for this role in the three tested worlds. Unchanged planning position and skill fit are explicitly communicated. The complete-tie presentation is covered by a dedicated deterministic test.

## Verification

- Backend: **92 passed**, including real PDF/DOCX parser regressions, extraction fallback, ownership, CSRF, bounds, resume exclusion, draft resumption, completion, legacy compatibility, scenario profile invariance and equality of factual graph / research / impact responses across worlds.
- Frontend: **88 passed**, including preservation of an existing workspace pace during legacy profile edits, new-user routing, saved-stage resumption, manual completion without a resume, labelled demo preservation, extraction confirmation, dial route scope, shared state, save rollback, role context updates, real comparisons, honest ties and existing roadmap tests.
- `pnpm build`: passed, including TypeScript compilation. `git diff --check`: passed.
- Browser: fresh manual journey on a separate loopback origin; three canonical skills added; 12-hour commitment and career interest saved; reload resumed at Direction; completion opened My Future with a selected computed role.
- Browser: uploaded repository `data/demo/demo_cv.docx` through the actual file chooser, used local extraction and confirmed Python as Programming. Other suggestions stayed unconfirmed.
- Browser: existing seven-skill demo profile entered My Future directly. Its saved 12-hour roadmap still showed 1 of 16 milestones complete, including completed Systems Analysis. A 24-hour milestone previewed Weeks 1–12 at 2 hours/week and Week 1 at 40; preview was restored to 12 without saving.
- Browser: scenario role context and Future Self updated; source pages hid the dial; existing profile retained its skills. Mobile 390×844 check had client width 375 and scroll width 375, with usable interests and keyboard learning-hours control.
- Real screenshots were captured and visually inspected. They are delivered in `outputs/onboarding-corrections` in this chat workspace; `docs/qa/onboarding-browser.json` records compact observations.

Commands: `.venv\Scripts\python.exe -m alembic upgrade head`; `.venv\Scripts\python.exe -m pytest -q`; `pnpm build`; `pnpm exec vitest run --config frontend/vite.config.ts --reporter=json --outputFile=../docs/qa/onboarding-vitest.json`; `git diff --check`.

## Remaining limits

Draft saving needs the server and the current browser session; there is no offline resume or cross-device account system. Unconfirmed extraction suggestions deliberately disappear after reload. Background and goals are captured transparently but are not new ranking inputs. Some computed priority skills are outside the bounded graph's displayed nodes; the planning panel and role details still name them, and the map highlights only nodes actually present. Dense phone graphs still require pan/zoom. Optional OpenAI extraction was preserved and regression-tested with provider mocks; this task's real upload used local extraction. No formal screen-reader or physical-device audit was performed. Pytest reports the existing Starlette/httpx deprecation warning.
