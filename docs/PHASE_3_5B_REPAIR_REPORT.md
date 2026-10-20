# Phase 3.5B Matchmaker repair and real verification

20 October 2026 (Asia/Kuala_Lumpur). Phase 3.5B only. **Real OpenAI tool-calling success verified after repair.** Phase 3.5C and Replit publishing were not started. No credentials, resume contents, private profile identifiers or raw provider responses are included.

## Findings

The reported Python lines dereferenced possibly missing values: the worker profile before reading its timestamp, the session owner before reading its token hash, and the execution returned by the cancellation lock. Python syntax compilation passed, but these were valid Pylance/Pyright optional-access concerns. Explicit guards and ownership return annotations now make those paths safe. A cancellation/deletion race returns 404 rather than dereferencing a missing execution.

The old combined `provider_or_validation_error` hid where failure occurred. Added allowlisted diagnostics for execution stage, HTTP status, known provider code, exception category and a fixed reference-validation reason. Exception messages, raw request/response bodies, arguments, keys and personal data are never echoed. Real traces established that OpenAI returned tool calls; one run failed in tool execution, and another completed two tools then failed in final validation with `invalid_reference`. The latter used 11356 real recorded tokens. An empty earlier usage dashboard did not identify the cause; this investigation does not infer the reason for that dashboard state.

The output schema had allowed arbitrary reference strings while the backend correctly required exact known role/skill/source references. Prompt instructions alone did not guarantee those identifiers. Repair:

- Tool `role_id` parameters now enumerate authorized current graph occupation IDs, explicitly describing the unprefixed tool format.
- Final generation schema pins the selected graph role, permits only displayed skills actually retrieved by authorized tools, and allows a source only after retrieving its evidence.
- Final section enums are limited to sections whose backing tool has run. No retrieved skills means an empty highlight list; no retrieved source means null evidence.
- Existing backend validation remains in place. Unknown references are still rejected, not silently accepted or guessed.
- The prompt distinguishes graph role IDs from tool occupation IDs and states the existing bounded turn/tool budget. The model still chooses its tools and order; no fixed research sequence was added.
- UI failure messages distinguish configuration, authentication, permission, quota/rate limits, request format and validation failures, with expandable safe details. The running message now says "Matchmaker worker started" rather than suggesting an OpenAI connection has been confirmed.

## Real repaired interaction

[Sanitized proof](qa/phase3_5b/repaired-real-verification.json). The existing FastAPI application was exercised through its ASGI HTTP adapter against the configured PostgreSQL database, using a disposable labelled manual Demo profile with six synthetic confirmed skills. A pass-through observer timed the existing provider function and recorded only timings, token counts and registered tool names; it changed no inputs or responses. Calls used the official HTTPS OpenAI endpoint with the configured `gpt-4.1-mini` and real server-side credentials. No provider mock or fake response was used.

Actual model-selected sequence:

1. get_ranked_matches
2. get_skill_gaps
3. get_ranked_matches
4. Final structured selection (no tool)

Terminal status: **completed**. Tool count: **3**. Recorded token usage: **21748**, equal to the four observed provider-response usage totals (1031 + 5030 + 5772 + 9915). Actual SDK request/response round trips: **5.875s, 1.442s, 1.431s, 3.112s**, total **11.860s**. Observed ASGI submission/background completion/read duration: **61.247s**, including substantial application/database work and the adapter waiting for the background task; this is not pure model latency or the production 202 response latency.

Both returned fit and gaps exactly matched the authoritative unchanged matcher/tool services. The selected role and highlighted skills were validated against the actual graph. PostgreSQL status, counters, result and event sequences matched API reads. The SSE endpoint replayed the six persisted events in order, then `done`; this repaired-run check verified terminal SSE replay, not a browser watching generation. A foreign client's snapshot and SSE requests both returned 404. Universe graph status remained ready, with nodes/edges unchanged. The disposable profile was deleted and its execution cascade deletion confirmed. Original user profiles were not modified. No real-person CV was used.

Earlier diagnostic traces remain separate: [first diagnostic](qa/phase3_5b/runtime-diagnostic.json), [reference diagnostic](qa/phase3_5b/reference-diagnostic.json). These are real failures preceding the successful repair, not mocked successes. The previous unsuccessful-verification report remains historical.

## Validation and files

Commands run with project Python and bundled pnpm:

```sh
python -m compileall -q backend/app/agents
pnpm dlx pyright --pythonpath .venv/Scripts/python.exe backend/app/agents
python -m pytest backend/tests -q --tb=short
pnpm test --maxWorkers=1
pnpm typecheck
pnpm build
python scripts/start.py
```

- Pyright: **0 errors, 0 warnings** across the agent folder.
- Backend: **83 passed**, including missing-execution race handling, safe error metadata/redaction and dynamic graph/retrieval schema checks.
- Frontend: **67 passed**, including actionable quota failure and safe detail rendering.
- TypeScript check and production build passed. No tests removed/skipped. One existing Starlette/httpx deprecation warning remains.
- No schema migration, dependency-lock, scoring, evidence, graph-layout or phase expansion was needed. Pyright was run ephemerally through pnpm dlx, without adding an application dependency.
- Modified: agent api/contracts/execution/orchestrator/registry, agent tests, frontend activity panel/API types/tests.
- Created: `backend/app/agents/diagnostics.py`, `backend/tests/test_agent_diagnostics.py`, this report and the three sanitized diagnostic/proof JSON files.

Local server was restarted to load the repair and the production frontend bundle. Reload `/universe` and start a **new** exploration; historical failed runs remain failed records. Replit remains on hold pending credits. This successful demo establishes one real provider interaction, not stress testing or guaranteed provider availability. A browser screenshot was not captured in this repair run. In addition to the ASGI probe, a real localhost HTTP request and live SSE stream were checked as described below; frontend interactions remain covered by the regression tests.


## Final actual localhost HTTP and live SSE check

[Network proof](qa/phase3_5b/http-repaired-verification.json). After restarting the real local server, a separate disposable Demo session submitted the UI's default question, "Which skills should I focus on for this role?", over `http://localhost:8000`. No ASGI test adapter, provider wrapper or mocked response was used for this check. The POST used the frontend's 15-second request timeout.

- Accepted in **11.507 seconds**; live SSE reached `completed` and `done` in **41.780 seconds** from submission.
- The model selected **get_role_requirements**; **1 actual completed tool call** and **4366 recorded tokens**.
- Returned requirements exactly matched the authoritative service; PostgreSQL result/status/counters matched the API.
- Live SSE delivered queued, running, tool_completed and completed in sequence and matched the saved snapshot.
- The Universe graph remained ready with unchanged nodes/edges; the disposable profile was deleted.
- This verifies a second successful real interaction and the ordinary HTTP/live-stream path. Provider-only round-trip latency was not separately instrumented for this network run; the earlier timing-observed run provides that measurement.

The model chose a different authorized tool for the default question, demonstrating that execution is not a fixed scripted sequence. This test does not claim a browser-rendered success screenshot. The application still uses its original bounded execution policy and requires no Phase 3.5C dependency.
