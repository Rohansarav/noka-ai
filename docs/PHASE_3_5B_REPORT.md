# Phase 3.5B — Agent execution, live activity and Universe enhancements

Latest status: subsequent repair and successful real OpenAI verification are documented in [the repair report](PHASE_3_5B_REPAIR_REPORT.md). The original findings below are historical.

20 October 2026. Implemented Phase 3.5B only. Local app: http://localhost:8000/universe. Replit publishing remains on hold pending owner credits. No Phase 3.5C work, GPU job, search-provider request or deployment was performed.

## Outcome and verification boundary

Matchmaker has a bounded OpenAI Responses function-calling loop, seven strict read-only tools, persistent session-owned executions/events, SSE and polling, cancellation, quotas and validated graph effects. Scout, Guide and Impact have configuration contracts only; Oracle is separately registered as an analytical service, not an executable agent. The approved loaded Universe arrangement and unchanged deterministic matcher remain authoritative.

**No OpenAI key is configured locally. Real provider-backed tool calling is UNVERIFIED.** The live application correctly records `ai_unavailable`, with zero tool calls/tokens and no substitute AI answer. Mocked provider tests exercise actual orchestration and journalling but are not a real provider trace. No fabricated successful interaction is included.

## Architecture and trust boundary

`agents/contracts.py` defines strict Pydantic request, argument, selection and event-payload contracts. `registry.py` supplies strict Responses function definitions. `tools.py` calls SQL/services directly, never internal HTTP. `orchestrator.py` lets the model independently choose authorized tools and their order; no scripted research sequence or simulated delays exist. Each provider turn receives prior tool outputs; the service executes only validated read-only calls.

The model selects factual sections and existing graph references, rather than authoring score-bearing prose. `assemble` requires the corresponding tool result for each selected section and renders its original facts. This deliberately limits narrative flexibility to prevent invented numerical scores, forecasts, evidence and SDG mappings. The final response schema cannot contain a score or arbitrary instruction. Existing Python match explanations, role requirements, gaps and reviewed rationale supply the displayed explanation. Scores remain skill-fit heuristics, distinct from forecast opportunity. Fit section data exactly equals the unchanged matcher response in tests.

The browser/model cannot choose a profile. The HttpOnly session determines its profile; accepted role IDs must occur among the current graph roles. Tools cannot access another profile or accept a profile ID, URL, SQL or write operation. The provider receives confirmed canonical skill fields only when it calls the corresponding tool, public graph entity references, and the bounded current question. Profile node identifiers are omitted from the initial provider context. Questions are capped, Unicode/control cleaned and contact/link patterns redacted before sending. Questions, raw resumes, provider prose, function arguments and chain-of-thought are not stored in events or application logs. `store=False` is passed to Responses; no provider-side retention guarantee beyond that flag is claimed.

Sessions are rechecked before publishing tool results. A saved profile revision change fails the run rather than mixing revisions. Deleting a profile/session cascades its executions/events; workers discard late results when their execution disappears. Same-origin/custom-header checks protect POST actions and body middleware caps agent requests at 8 KiB before parsing. Error messages contain fixed safe codes, never provider exception text. Public evidence and curation were not changed.

## Bounds and lifecycle

Environment settings (also listed without secrets in `.env.example`):

| Setting | Default | Valid range |
|---|---:|---:|
| AGENT_MAX_TOOLS | 5 | 1–10 |
| AGENT_MAX_TURNS | 4 | 1–8 |
| AGENT_TIMEOUT_SECONDS | 60 | 5–120 |
| AGENT_MAX_OUTPUT_TOKENS | 1200 per turn | 256–3000 |
| AGENT_DAILY_QUOTA | 20 starts/session/rolling 24h | 1–100 |
| AGENT_MAX_CONCURRENT | 2 active/session | 1–4 |
| AGENT_GLOBAL_CONCURRENT | 8 active/database | 1–16 |

At most one tool call per model reply is accepted; parallel tool calling is disabled. Turns include the final selection, so a run may finish before using the full tool budget. Provider timeout is the lesser of 20 seconds and remaining execution deadline, with SDK retries disabled. Available provider token totals are persisted, including late responses discarded after cancellation. Failed/missing-key/cancelled starts count toward the rolling quota. These are anonymous-session limits; clearing cookies can create another session, so they are not an account-level abuse prevention system.

Start admission serializes with a PostgreSQL transaction advisory lock plus an owner-row write lock (SQLite serializes writes). Counts and insertion share that transaction. Status/event updates obtain an execution write lock before allocating a sequence. Terminal transitions check current status, so repeated cancel/recovery does not append duplicate terminal events. No application-level automatic provider retry or event replay executes tools twice.

States are queued → running → completed/failed, or queued/running → cancelled. Missing-key failure can go directly queued → failed. Cancellation is logical and immediately terminal: any in-flight provider request may finish within its bounded timeout and may incur usage, but no late tools/results are published. Token counts are not cost estimates.

**Worker/restart policy:** FastAPI background work is process-local, not a durable queue. Only execution/event records survive a crash; the question is intentionally not persisted. On the next authorized status/stream request or execution admission, expired queued/running leases become `failed/deadline_or_interrupted` with a terminal event. A request before the old deadline can still see the prior queued/running status. Idle rows are not swept by a separate scheduler. No interrupted run is silently resumed or replayed. Submit a new exploration to retry. A durable queue and explicit private-question retention policy would be separate future work. The current page does not provide history or restore its selected run ID after a full page reload; stream interruption recovery works while the view remains mounted.

## Database migration and journal

Alembic `0004_agents.py`, down-revision `0003`, was applied successfully to the configured **PostgreSQL** database. `/api/ready` now requires `0004` and reports connected/current/built. `alembic check` reported no new upgrade operations (no schema drift). No evidence import was run.

`agent_executions`: opaque random id, hashed session FK, agent, status, created/updated/deadline timestamps, configured model, tool count, token total, event sequence, safe error code and nullable server-assembled JSON result. Owner FK cascades deletion; session lookup is indexed.

`agent_events`: composite primary key `(execution_id, sequence)`, timestamp, agent, event type, status, fixed safe message and Pydantic-validated JSON payload. Payload allowlist is `tool` and `related_entity`; neither question nor arbitrary provider output can be a payload. Types: queued, running, tool_completed, completed, failed, cancelled. Sequence allocation and event insert are committed with the corresponding execution update. Timestamp and sequence describe actual operations, not internal reasoning.

## Tool registry

| Tool | Input | Authoritative source |
|---|---|---|
| get_current_profile | empty object | Current owner's confirmed flag, country preference, role interests |
| get_confirmed_skills | empty object | Current owner's canonical skills and self-rated levels |
| get_ranked_matches | empty object | Existing `match_profile`, unchanged scores/methodology |
| get_role_requirements | current graph role_id | Attributed RoleSkill/Skill rows |
| get_skill_gaps | current graph role_id | Existing matcher gaps |
| get_role_evidence | current graph role_id | Role/source rows with explicit sector-proxy limitation |
| get_reviewed_sdg_connections | current graph role_id | Explicit role links and links of its requirement skills, human_reviewed with reviewer/time |

Skill–SDG records retain skill identity and are explicitly displayed as skill links; they do not imply a role–SDG link or measured impact. Empty results remain empty. Source IDs and stored source URLs stay attributable.

## API and UI

- `POST /api/agent-executions`: strict agent/question/role context; returns 202 and opaque execution, schedules bounded work.
- `GET /api/agent-executions/{id}`: authorized snapshot, all bounded persisted events and terminal result; polling fallback.
- `GET /api/agent-executions/{id}/events`: authorized SSE `activity` records, sequence IDs/Last-Event-ID replay, heartbeats and terminal `done`; checks ownership during streaming and stops on disconnect/expiry/completion. DB reads run off the event loop, without retaining a stream-long DB transaction.
- `POST /api/agent-executions/{id}/cancel`: same-origin, authorized, idempotent terminal cancel.

All execution responses are no-store. Missing/foreign IDs return the same 404 behavior. Existing APIs/routes remain intact.

`AgentActivityPanel` is reusable and collapsible, shows real persisted steps and safe failures, announces status politely and exposes cancellation. SSE triggers authoritative GET snapshots; an independent bounded-frequency polling path survives stream errors. Activity links point only to current graph entities. A selected role gets an Explore with Noka anchor in its detail panel and the question/action below the unchanged workspace.

Final effect allowlist: focus a known role, highlight existing owned/required skill nodes, and open a known source card/link. The server requires retrieved evidence/skills and validates IDs; the client independently checks the current graph, profile timestamp, effect keys, role/skill types and source existence. No arbitrary browser command or URL is accepted. Ordinary selection/reset clears AI highlights. Results describe the run's original role even if the user selects another role meanwhile.

`UniverseLoading` is used for the route chunk, data request and lazy canvas. Its eager, small CSS draws decorative unlabelled nodes, curves and a Noka compass inside the canvas area. Its expandable discovery explanation promises only existing confirmed skills, heuristic roles, gaps and reviewed links where available. Accessible loading status, responsive rules and reduced motion are included. It unmounts immediately on data/error; no minimum duration, research narrative, animation-driven request or added animation dependency exists. The loaded graph layout/pan/zoom/filters/list remain intact.

## Files

Created: `backend/app/agents/{__init__,contracts,registry,tools,execution,orchestrator,api}.py`; `backend/migrations/versions/0004_agents.py`; `backend/tests/test_agents.py`; `frontend/src/universe/{AgentActivityPanel.tsx,AgentActivityPanel.test.tsx,agent-api.ts,UniverseLoading.tsx,universe-loading.css}`; this report and `docs/qa/phase3_5b/`.

Modified: backend `models.py`, `config.py`, `main.py`, `profile_security.py`, `career_graph.py`, readiness fixture `test_api.py`; frontend `App.tsx`, `CareerUniverse.tsx`, `CareerGraph.tsx`, `CareerDetailPanel.tsx`, `CareerUniverse.test.tsx`, `universe.css`; `.env.example`, `README.md`, `AGENTS.md`. No dependency or scoring change.

## Actual verification

Commands used with `.venv/Scripts/python.exe` and the workspace's bundled pnpm executable:

```sh
python -m alembic upgrade head
python -m alembic check
python -m pytest backend/tests -q --tb=short
pnpm typecheck
pnpm build
pnpm test --maxWorkers=1
python scripts/start.py
```

Final backend suite: **75 passed** (59 existing + 16 new). Final frontend suite: **66 passed** (58 existing + 8 new). Typecheck and production build passed. One pre-existing Starlette/httpx deprecation warning remains. No tests were removed or skipped. An initial combined backend/frontend run hit an existing one-second canvas test wait; the complete frontend suite passed when run independently, without weakening its assertion or timeout. Provider doubles explicitly exercise strict definitions, model-selected tool invocation, sequence persistence, real matcher equality, unauthorized tool/argument rejection, fabricated score/result rejection, cancellation during a provider call, terminal idempotence, deadline/provider timeout, missing key, per-session/global concurrency, rolling quota, body limit, reviewed source attribution, cross-session denial, SSE completion/replay and GET fallback. UI tests cover progression, completion, failure/cancel, selected-role context, validated highlights/stale/unknown/extra effects, SSE-unavailable polling and accessible loading/discovery.

Actual HTTP → PostgreSQL probe created a disposable labelled six-skill manual Demo profile (no real CV/person). It submitted Matchmaker, observed `failed/ai_unavailable`, read its two real persisted events directly from PostgreSQL, verified a foreign client's 404 and terminal SSE, then removed the disposable profile and verified execution cascade deletion. [Safe proof](qa/phase3_5b/live-verification.json) contains no cookie/profile identifier. Existing browser Demo separately confirmed that the failure leaves the graph and scores usable. **This is a real unavailable execution trace, not successful live LLM verification.**

Public data remained 25 roles, 35 skills, 875 requirements, 114821 demand observations, 17 goals, 169 targets and 7 reviewed links, with 2020-02-01..2026-10-09 history. No source/curation was invented or re-imported.

Responsive browser checks: 1440×1100, 768×1024, 375×812. Document client/scroll widths were equal at 1425, 753 and 360 pixels respectively (scrollbar excluded), with no horizontal overflow. Activity panel widths included 483px tablet and 324px mobile. Browser warnings/errors were empty during observed checks. Screenshots in `docs/qa/phase3_5b/` show the labelled Demo, real unavailable state and loading component; they are not evidence of a successful provider answer. The expanded mobile discovery loader grew naturally to 513px with no clipping or horizontal overflow. [Desktop activity](qa/phase3_5b/activity-1440.png), [tablet activity](qa/phase3_5b/activity-768.png), [mobile activity](qa/phase3_5b/activity-375.png), [desktop loading](qa/phase3_5b/loading-discovery-1440.png), [mobile loading](qa/phase3_5b/loading-discovery-375.png). Temporary viewport overrides were reset.

## Remaining limits and Phase 3.5C prerequisites

A valid server-side OpenAI key, access to the configured model and a successful real provider tool trace are still needed to verify the integration externally. Configure the key locally, restart, select a role and run Explore with Noka; inspect actual persisted tool events/result, not just a response status. No live success is claimed here. The constrained evidence-selection response intentionally has less narrative flexibility than free-form AI prose. PostgreSQL admission and persistence were smoke-tested; stress/load and multi-worker crash testing were not performed. Responsive checks do not establish physical-device or full accessibility certification.

Replit credits and explicit publishing authorization are needed before production hosting checks. Phase 3.5C requires an explicit owner request and its own scope; any future Scout/search or Guide/Impact execution needs separately reviewed tools, source/curation rules, budgets and privacy tests. Durable job resumption, account-level quotas and execution retention cleanup need explicit design before larger-scale deployment. No scenario, roadmap, forecast, chat history, agent debate or autonomous profile mutation was added.

Implementation reference: [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling). Public source provenance remains in [DATA_SOURCES.md](DATA_SOURCES.md).
