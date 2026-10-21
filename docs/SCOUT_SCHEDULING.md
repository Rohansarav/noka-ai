# Scout scheduling on Replit

The web service uses Autoscale. Do not run a timer loop inside it: Autoscale can scale to zero. Replit's separate Scheduled deployment runs a command on a schedule and stops afterward. This was verified against the [official deployment types documentation](https://docs.replit.com/features/publishing/deployment-types) on 21 October 2026.

Publishing remains subject to the owner's authorization and available credits. No scheduled deployment or public web deployment has been activated by this build.

## Configure the scheduled job

Create a separate Scheduled deployment from the same reviewed repository revision:

- Build command: `uv sync --frozen --no-dev`
- Run command: `uv run --no-dev python -m backend.app.scout`
- Schedule: `0 8 * * *`
- Time zone: `Asia/Kuala_Lumpur`
- Job timeout: 300 seconds. Maximum application network work is four searches, one extraction batch, and three bounded publisher metadata requests, each with a 25-second network timeout.
- Deployment secrets: the same production PostgreSQL `DATABASE_URL` as the web service, `ENVIRONMENT=production`, and `TAVILY_API_KEY`.

The command has no public HTTP trigger and accepts no resumes or private profile input. A PostgreSQL advisory transaction lock prevents overlapping refreshes. A persisted one-hour cooldown limits repeated runs. Each finished run records success, failure or unavailable credentials and its actual tool events. Findings are URL-deduplicated; previously stored findings survive failed refreshes. An abrupt process termination is visible in Replit job logs; it cannot be represented as a successful refresh.

Use the scheduler's failure alerts. Inspect `/api/intelligence` or Intelligence Radar for the latest run and last successful refresh. A skipped cooldown/overlap is a neutral exit, while a provider failure or missing credentials exits nonzero. Unknown publication dates remain unknown. Retrieved content is untrusted evidence and is never executed as instructions.

## Verify after authorization

Run the job once in the Scheduled deployment, inspect its actual logs and persistent `scout_run` record, then wait for a scheduled invocation to verify the clock and timezone. A local successful CLI run does not prove the remote scheduler has been enabled.

For evidence-based outlook records and pending SDG proposals after the initial real public-data import, run:

```sh
uv run python -m backend.app.outlooks
uv run python -m scripts.propose_impact
```

These are explicit, idempotent initialization commands; they do not invent human approvals. A trained Oracle artifact is checked into `ml/artifacts/`; retrain explicitly with `uv run python -m ml.train` after an appropriate real-data import.
