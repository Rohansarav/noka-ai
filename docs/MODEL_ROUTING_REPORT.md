# Phase 3.5B model routing update — 22 October 2026

Implemented the owner-requested split: OPENAI_EXTRACTION_MODEL=gpt-4.1-mini for resume/manual extraction; OPENAI_GUIDE_MODEL=gpt-6-sol for Guide. Both have matching code defaults. OPENAI_MODEL remains the Scout research model. Local ignored .env was updated without changing keys. No Phase 3.5C work.

Files: backend/app/config.py, backend/app/skill_extraction.py, backend/app/agents/orchestrator.py, backend/app/agents/execution.py, .env.example, README.md, backend/tests/test_model_settings.py, backend/tests/test_profile_analysis.py, backend/tests/test_agents.py, and this report. Guide journal entries now record the Guide model.

Validation command:

```powershell
.venv/Scripts/python.exe -m pytest backend/tests/test_model_settings.py backend/tests/test_profile_analysis.py backend/tests/test_profiles.py backend/tests/test_agents.py backend/tests/test_agent_diagnostics.py backend/tests/test_software_and_impact.py -q
```

Result: 68 passed, one existing Starlette/httpx deprecation warning. git diff --check passed. Tests cover environment overrides, extraction routing, Guide provider routing and persisted model identity, plus existing extraction/agent behavior.

Live verification: a synthetic programming sentence passed through the real extract() path using gpt-4.1-mini and returned mode=openai with one candidate in 8.5 seconds. No user resume was used. Guide routing was verified with provider doubles; live Guide generation was not retested. Existing timeouts/output budgets still apply and may limit Guide requests.

The initial restart with the prior runtime did not serve HTTP; the workspace .venv runtime restored the service. Backend is running via scripts/start.py; /api/health and /api/ready both returned HTTP 200. Restart command: .venv/Scripts/python.exe scripts/start.py.

Deployment: local only. Replit publishing remains on hold. Blockers: none for the requested split. Human review: owner explicitly authorized the model choices; implementation review remains pending. No mapping proposals were approved automatically. Changes are committed with message "Split extraction and Guide model configuration"; use git log -1 for the commit identifier.
