# Phase 3.5B — real interaction verification

Latest status: subsequent repair and successful real OpenAI verification are documented in [the repair report](PHASE_3_5B_REPAIR_REPORT.md). The original findings below are historical.

20 October 2026. **Real verification attempted; unsuccessful. Phase 3.5C not started.** No mocks, fake credentials, substituted provider responses, architecture changes or automated retry were used. The existing local server was restarted to load its newly configured key.

| Check | Actual result |
|---|---|
| Secret configuration | Key configured; never printed or saved in this report |
| Configured model | gpt-4.1-mini |
| Real OpenAI authentication/model access | Read-only model metadata request succeeded |
| Real Matchmaker attempt | Existing application POST returned an accepted execution; terminal status failed |
| Terminal error | provider_or_validation_error |
| Completed tool calls | 0; model tool selection/invocation not verified |
| Recorded token usage | 0; provider billing usage was not independently retrieved |
| PostgreSQL persistence | Status, counters, result and event sequence matched API reads |
| SSE delivery | queued → running → failed, followed by done; events matched persisted snapshot |
| Cross-session access | Execution snapshot and SSE both returned 404 |
| Universe regression check | Demo graph remained ready; nodes and edges unchanged through HTTP API |
| Cleanup | Disposable manual demo profile deleted; execution/event cascade confirmed |

A labelled six-skill synthetic manual demo was used, without a real resume or personal identifiers. One Matchmaker interaction was submitted. It produced no role/skill result, so returned-data equivalence to the authoritative matcher could not be established. Passing mocked tests from the implementation phase do not prove real provider success.

Observed POST acceptance: **12.462 seconds**. Observed submission-to-SSE-completion: **37.586 seconds**. Persisted execution creation-to-terminal: **26.490 seconds**. These include database/application work and stream observation. **Individual provider HTTP latency is unavailable** because the existing application does not instrument it; these numbers must not be labelled pure model latency.

The application deliberately stores a sanitized combined provider/validation error and does not retain the underlying exception/HTTP status. The root cause is therefore unresolved. Successful model metadata retrieval establishes authentication/model visibility, but does not establish successful Responses generation or available generation quota. A safe diagnostic capturing provider HTTP status/error code or validation error category is needed to identify this failure before another generation attempt. No such application change was made during this verification.

The model's documented Responses/function-calling/structured-output capabilities were checked against [official OpenAI documentation](https://developers.openai.com/api/docs/models/gpt-4.1-mini). This documentation check is separate from account-specific execution success.

[Sanitized real probe evidence](qa/phase3_5b/real-provider-verification.json) records actual timestamps and checks, without cookies, profile IDs, keys, private fields or raw provider credentials. Application readiness was connected/current/built. No UI/browser interaction or new full test-suite run is claimed for this verification; Universe integrity was checked through its real API. The earlier mocked suites remain historical implementation evidence.
