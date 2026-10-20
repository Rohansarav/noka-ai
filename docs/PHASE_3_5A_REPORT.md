# Phase 3.5A — Interactive Career Universe

20 October 2026 · Implemented Phase 3.5A only. Local preview: http://localhost:8000/universe. Replit publishing remains on hold pending credits. No Phase 3.5B agent/activity functionality was started.

## What changed

`/universe` is a dedicated, read-only discovery view built with **@xyflow/react 12.12.0**, installed using the existing pnpm workflow. My Universe is in the primary sidebar. The homepage's Build My Future journey uses the shared `useProfile().journeyPath`: confirmed profiles enter Universe; missing/draft profiles enter intake. Existing routes remain available, including full matches and public role evidence. The graph is lazy-loaded independently of the existing pages.

The canvas supports pan, wheel/pinch zoom, zoom controls, fit, node selection, selected-connection highlighting, focus and reset. Native React Flow keyboard selection is connected to the same detail state as pointer input and role/list buttons. Selection focus transitions use 240 ms, or zero under reduced-motion preferences. Filters fit immediately to avoid chasing moving targets. Layout is deterministic and uses no additional layout dependency. Coordinates and selection are presentation state, never database writes.

The existing cream/mint/aqua/powder-blue design tokens remain authoritative. Custom cards distinguish confirmed skills, role-specific gaps, career directions, official SDG targets and goals. SDG colours are decorative accents; text remains dark/readable and no official logos are used. Detail panels expose requirements, self-rated proficiency shortfalls, deterministic methodology, review state, source links and existing navigation. Desktop uses a contextual side panel; smaller widths stack it beneath the compact graph. A separately selectable list provides the same detail access without using the canvas.

## Backend contract and composition

**GET `/api/profiles/current/career-graph`** resolves the opaque HttpOnly session using `active_session`, finds its profile and applies `owned_profile`. There is no profile-ID parameter or internal HTTP call. All responses use `Cache-Control: no-store`. A missing/expired session returns an honest `no_profile` graph without creating a session. Sparse/unconfirmed profiles return actual profile/skill nodes and `insufficient_profile_information`, with no fabricated career matches.

`build_career_graph` is a dedicated aggregation service. It calls the existing, unchanged `match_profile` for ranking, scores, coverage, explanations and priority gaps. It then joins real role requirements and sources. No scoring algorithm, historical observations, curation or persistence schema was changed. No migrations or imports were needed.

Composition bounds:

- One central profile.
- All confirmed skills accepted by the current profile API, capped at that API's 60-skill maximum; the present canonical catalogue has 35 skills.
- Top **three** existing deterministic matches.
- Top **three** priority gaps per displayed role, in the matcher's importance/name order.
- Up to **six** explicit human-reviewed SDG links whose entities are displayed; reviewer and review timestamp must also exist.
- Hard response limits: **88 nodes, 300 edges**.

Types: `profile`, `owned_skill`, `required_skill`, `role`, `sdg`, `sdg_target`. IDs use `profile:`, `skill:`, `role:`, `sdg:` and `sdg_target:` namespaces. A canonical skill has only one node: a partial confirmed skill stays `owned_skill`. A `required_skill` node means an absent, displayed priority requirement, not a global claim about the person.

Edges: `has_skill`, `requires_skill`, `missing_skill`, `contributes_to_target`, `target_belongs_to_goal`. Role requirement edges retain O*NET importance, source IDs, critical status and the per-role proficiency gap. SDG edges retain the actual link ID, rationale, source and review status. The API name `contributes_to_target` is presented as **contextual relevance**, never measured impact or UN endorsement. No role→SDG connection is inferred merely because a skill connects to a target.

The API retains both a requirement edge and a priority gap edge where appropriate. The renderer draws the gap line once in that case to prevent duplicate overlapping paths; the complete evidence remains available to the detail panel and API consumers. Role panels describe requirements **in this view**, with links to complete Role Matches and occupational evidence.

Output includes `status`, `profile_revision`, `generated_at`, `nodes`, `edges`, `sources`, `methodology`, and `limitations`. `profile_revision` is the existing saved-profile update timestamp, not a newly introduced optimistic-lock version. Node/edge ordering is stable; generation time changes per request. Profile changes/deletion clear the graph query cache.

## API response example

The complete strict response captured from a disposable, labelled six-skill manual demo against PostgreSQL is [career-graph-example.json](qa/phase3_5a/career-graph-example.json). Its profile identifier was replaced with `demo-profile`; public identifiers, source references, scores and relationships were preserved. This is illustrative private input matched against real occupational evidence, not a real person's CV.

Selected fields from that response are shown below; other nodes and required response fields are omitted from this excerpt:

```json
{
  "status": "ready",
  "profile_revision": "2026-10-20T09:32:02.266924+00:00",
  "generated_at": "2026-10-20T09:32:12.034803Z",
  "nodes": [
    {
      "id": "role:15-1242.00",
      "type": "role",
      "entity_id": "15-1242.00",
      "label": "Database Administrators",
      "score": 19.4,
      "review_status": "human_reviewed"
    }
  ],
  "edges": [
    {
      "id": "missing_skill:role:15-1242.00:skill:2.A.1.b",
      "type": "missing_skill",
      "source": "role:15-1242.00",
      "target": "skill:2.A.1.b",
      "source_ids": ["9dd19c2637a1cfd0a0ed99c1e115a4e87910e1dd"],
      "importance": 3.75,
      "gap": 1.0,
      "supporting_id": "15-1242.00:2.A.1.b"
    }
  ]
}
```

The displayed 19.4 is the unchanged matcher's heuristic score for that particular six-skill test profile. It is not a forecast or probability. The browser demonstration uses a separate, explicitly labelled eleven-skill Demo profile and therefore has different scores.

## Files

Created:

- `backend/app/career_graph.py`, `career_graph_schemas.py`, `career_graph_api.py` — aggregation, strict contracts and session-derived route.
- `backend/tests/test_career_graph.py` — ownership, evidence, composition and consistency checks.
- `frontend/src/universe/CareerUniverse.tsx` — page/query/filter/list orchestration.
- `frontend/src/universe/CareerGraph.tsx`, `CareerNodes.tsx` — React Flow rendering, accessible selection and focus.
- `frontend/src/universe/CareerDetailPanel.tsx`, `CareerGraphLegend.tsx` — evidence/details and visual key.
- `frontend/src/universe/universe-types.ts`, `universe-api.ts`, `universe-layout.ts`, `universe.css` — contracts, client checks, deterministic presentation and scoped styling.
- `frontend/src/universe/CareerUniverse.test.tsx`, `universe-layout.test.ts` — page behavior and pure presentation tests.
- This report and `docs/qa/phase3_5a/` response, verification and screenshots.

Modified:

- `backend/app/main.py` — register graph router; existing routes retained.
- `frontend/src/App.tsx` — Universe navigation/route and profile-dependent homepage journey.
- `frontend/src/profile-api.ts` — shared journey selector.
- `frontend/src/ProfilePages.tsx` — graph cache invalidation and profile-card Universe link.
- `frontend/src/App.test.tsx` — retain navigation regression, now expecting nine primary links.
- `package.json`, `pnpm-lock.yaml` — React Flow dependency and its lockfile resolution.
- `README.md`, `AGENTS.md` — current phase/handoff information.

## Verification

Commands executed:

```sh
pnpm add @xyflow/react
pnpm typecheck
pnpm build
pnpm test --maxWorkers=1
python -m pytest backend/tests -q --tb=short
python scripts/start.py
```

The workspace's bundled pnpm executable and `.venv/Scripts/python.exe` were used where those commands were not on PATH.

- **59 backend tests passed**, including all existing tests and ten new graph tests. One existing Starlette/httpx deprecation warning remains.
- **58 frontend tests passed**, including existing navigation/intake/evidence tests and fifteen new Universe tests. Two tests timed out during an initial heavily parallel run alongside a build; they passed when isolated, and the complete suite passed with one worker. No tests were removed or skipped.
- **Typecheck and production build passed.** The renderer is a separate lazy chunk; no graph/database/layout framework was added to Python.
- Backend graph tests verify foreign/missing sessions, sparse profiles, IDs, real requirement attribution, owned/partial distinctions, reviewed-only SDGs, no unsupported mappings, exact matcher scores, limits and stable ordering.
- Frontend tests verify confirmed/missing/draft homepage navigation, loading/error/retry, node/detail selection, filtering without writes, accessible list selection, sparse profiles and absent SDG explanations. JSDOM page tests use an explicitly labelled canvas adapter because JSDOM cannot measure a pan/zoom canvas; **real React Flow** interactions were checked in the live browser.
- Actual HTTP→PostgreSQL verification: an unauthenticated graph returned `no_profile`; a disposable six-skill Demo profile returned **20 nodes / 47 evidence edges / 3 reviewed SDG links**, and its three scores exactly equalled the existing matches endpoint. The disposable API profile was removed afterward. Safe proof: [live-verification.json](qa/phase3_5a/live-verification.json).
- Public evidence remained **25 roles, 35 skills, 875 role requirements, 114,821 demand observations, 17 goals, 169 targets and 7 curated links**, with the same **2020-02-01..2026-10-09** observation range. No public evidence import or update was performed.
- Existing browser Demo profile: manual review/edit/save still led to full matches. Science and Instructing were explicitly added as illustrative manual input to exercise existing reviewed relationships; no new public SDG links were created. Its Universe showed **22 nodes / 57 evidence edges**, three roles and three SDG goal/target chains.
- Browser keyboard Enter selected a real role, opened requirements/methodology and highlighted its real edges; Escape cleared selection in the final build. Pointer/list selection and SDG Target 7.2 displayed the stored solar-engineering rationale. Background dragging changed the viewport translation; zoom-in changed scale from 0.307519 to 0.369023. Fit/reset/filters/zoom controls were exercised.
- Responsive checks at **375×812**, **768×1024**, **1440×1100** found document widths of **360**, **753**, **1425** respectively (the 15px scrollbar is excluded), with no horizontal page overflow. The 375px canvas and stacked panel were each 322px wide. The mobile list selected Target 7.2 and its detail anchor opened the same reviewed rationale. Screenshots: [desktop](qa/phase3_5a/universe-1440.png), [tablet](qa/phase3_5a/universe-768.png), [mobile canvas](qa/phase3_5a/universe-375.png), [mobile details](qa/phase3_5a/universe-375-details.png). Browser error/warning logs were empty during the final checks. Temporary viewport overrides were reset afterward.

## Run and inspect

With the existing Phase 3 database configured, run `pnpm install --frozen-lockfile`, `pnpm build`, then `uv run python scripts/start.py`. Open `/universe`. No schema migration or additional AI key is required for this phase. Existing intake, matches, role catalogue, SDG explorer and design gallery remain available.

## Limits and Phase 3.5B handoff

This is a bounded view, not the entire ontology. Skill fit is self-reported and heuristic; geography is not a claim about vacancies. A sparse profile intentionally has no role matches. Unreviewed/unsupported SDG relationships remain absent. Pan/zoom controls and the list alternative remain important on small screens and for dense profiles. Responsive viewport checks do not establish physical-device testing or a complete accessibility audit.

No ML, Tavily, conversations, agent runs or simulated activity were implemented. Replit remains unverified/on hold. No new GPU work was used.

Phase 3.5B can reuse the typed entity IDs, source references, profile timestamp, read-only aggregation boundary, selected-node context, detail panel and query invalidation. Authentic execution/activity requires its own authorized run/event persistence and real backend action instrumentation; selection animations and graph generation timestamps must not be presented as agent activity.

Implementation references: [React Flow accessibility](https://reactflow.dev/learn/advanced-use/accessibility), [ReactFlow component contract](https://reactflow.dev/api-reference/react-flow), and [fit-view options](https://reactflow.dev/api-reference/types/fit-view-options). Existing public-source attribution remains in [DATA_SOURCES.md](DATA_SOURCES.md).
