# NOKA — Codex Implementation Playbook

**Objective:** Ship Noka, a light-themed, live Replit-deployed AI workforce navigator, solo, in three days. Execute one phase prompt at a time. All data must be real, cited, or explicitly identified as example/demo data.

## Operating instructions

1. Create one GitHub repository and connect it to Replit. In Codex, start with Phase 0, inspect results, run tests, commit, then proceed in order. Never paste every phase simultaneously.
2. At the end of *each* phase, ask Codex for: files changed, commands run, test results, deployment status, blockers, and commit message. Require a clean, running application before continuing.
3. Replit is the compulsory deployment platform. Publish a public working `.replit.app` URL as soon as Phase 0 is functional. Do not assume a workspace preview is a public production deployment.
4. OpenAI keys, search keys, and scheduled-job tokens are server-side environment secrets only; never put them in frontend bundles or commits.
5. All GPU work, training, or fine-tuning, if performed, **must** run on RunPod. CPU-only scikit-learn baselines may run on Replit/local development; the hackathon's precise RunPod terms take precedence.
6. If an external service cannot be reached or authorized, keep the site functional and show an explicit unavailable/last-successful timestamp. Never silently fabricate data.
7. Major milestone deadline: fully deployed core journey by the end of Day 1; functioning predictive system by end of Day 2; lock features and rehearse on Day 3.
8. Write comments for important functions

---

## Shared master specification — paste first in Codex and ask it to create `docs/PRODUCT_SPEC.md` and `AGENTS.md`

> You are the senior full-stack engineer and technical lead for NOKA, a hackathon product with a strict three-day solo-delivery deadline. Build production-like, minimal, testable code. Replit Core is mandatory for hosting and publishing. Optimize for reliability, clarity, speed, accessible UX, and a 3-minute live judge demo. Implement only the current phase requested; do not race ahead into future phases.
>
> Product: Noka — “Navigate tomorrow's work, today.” Users upload PDF/DOCX/text resumes or manually edit skills, receive a structured profile, matches to curated future roles, skill gaps, AI and labour-market signal feeds with publication/retrieval dates, four-week sector-demand ML forecasts, an interactive 2030 three-scenario simulator, personalized reskilling pathways with persisted progress, and role/skill explanations mapped to applicable United Nations Sustainable Development Goals and official targets.
>
> Three scenarios: AI Acceleration, Governed AI, Human–AI Collaboration. A four-week demand forecast is statistical, tied to trained sector-level time series, and must not be called a 2030 job forecast. Long-run scores are scenario-adjusted planning indices grounded in WEF/other published evidence and stated assumptions. Forecast outputs must carry geography, granularity, horizon, forecast timestamp, actual evidence, model version, and uncertainty/evaluation status.
>
> Design direction: LIGHT THEME ONLY by default, inspired by the user's SDC Hackathon screenshot: predominantly warm off-white and white, airy pale mint / aqua / powder-blue pastel gradients, soft shadows, rounded 20–28px cards, friendly illustrations/iconography, excellent whitespace, dark navy text, accessible contrast, blue primary buttons, subtle animations, professional yet optimistic. No black/neon hacker styling. Brand name Noka, avoid implying endorsement by SDC or copying the website's mascot/trademarks. Responsive desktop/mobile. Keep one consistent component library. Use lucide-react, Tailwind, shadcn/ui primitives, Recharts and motion sparingly. All loading/error/empty states must be beautiful and honest.
>
> Tech: Vite + React + TypeScript + Tailwind + React Router + TanStack Query for frontend; Python FastAPI + Pydantic v2 + SQLAlchemy + Alembic for API; PostgreSQL using `DATABASE_URL` in deployed Replit, with a documented local SQLite dev fallback if needed; OpenAI SDK for structured skills extraction and narrative content; Tavily for public search signals; pandas/scikit-learn/XGBoost for forecasting as appropriate; pytest and Vitest. Serve the built React app from FastAPI in production so a single Replit Web service serves both `/` and `/api/*`. Use ports and start commands compatible with Replit deployment. Avoid unnecessary Docker/microservices, LangChain agent swarms and GPU inference endpoints.
>
> Repository: `/frontend`, `/backend/app`, `/backend/tests`, `/ml`, `/data` (only small licensed/derived artifacts), `/scripts`, `/docs`, `/public`. Provide `.env.example`, `README.md`, `.gitignore`, dependency locks, migrations, one-command dev instructions, production build and start script, `/api/health` and `/api/ready`. Source code and dataset licensing citations belong in `/docs/DATA_SOURCES.md`.
>
> Contract first: JSON API responses use strict schemas. Use TypeScript types generated from or aligned with Pydantic schemas. All user-specific records belong to one anonymous server-created session/profile ID; do not implement complex auth unless absolutely necessary. Session IDs must be unguessable and ownership verified to prevent users reading each other's resumes. Limit uploads to 5 MB and accepted safe types. Strip PII from logs. Do not upload user resumes to third-party search tools. Keep API keys entirely server-side.
>
> Required business entities: profiles, profile_skills, canonical_skills, roles, role_skills, source_documents, ai_signals, job_signal_snapshots, demand_observations, forecast_runs, forecast_points, scenario_definitions, role_scenario_scores, learning_plans, learning_tasks, progress_events, sdgs, sdg_targets, role_sdg_links, skill_sdg_links, and ingestion_runs. Simplify table count pragmatically but retain source lineage. The model implementation must use **only** time-valid information for evaluation; never fabricate forecasts or performance metrics.
>
> Source strategy: Indeed Hiring Lab open historical sector-level job-posting indices (initially United States or another covered country); Indeed Hiring Lab AI posting-mention series *only if history/schema/time alignment is verified*; official UK ONS job adverts by occupation as optional secondary dataset; WEF Future of Jobs 2025 for long-run outlook/context; O*NET downloadable occupational database and skills mappings subject to attribution/license; UN official 17 SDGs and targets; Tavily for public, dated AI advancements and discoverable job signals. Data from distinct geographies and occupation granularities must not be presented as interchangeable. Lack of skill-level time series must be acknowledged prominently.
>
> Always preserve a working seeded sample journey independent of third-party API availability. The sample profile is clearly marked “Demo profile”; downloaded public datasets/observations remain real. Site must not falsely say “live” unless the refresh process has succeeded; show last-successful refresh and source timestamps. No invented posting volume, confidence percentage, salary, or model improvement.
>
> For each task, first inspect existing code and preserve previous functionality. Implement vertical slices and tests. Return exact commands to run, evidence of tests, known limitations, and what you need from me. Never claim Replit was published or an API was tested without proof.

---

# PHASE 0 — Repository, architecture, deployable skeleton

**Goal:** Working public-facing app and API in Replit before building features.

**Codex prompt:**

> Implement Phase 0 only according to `docs/PRODUCT_SPEC.md` and `AGENTS.md`. Start by checking the repository. Create the Vite React TS app and FastAPI backend with a single production serving arrangement: FastAPI serves `/api/*` and the frontend's compiled `dist` for other routes (SPA fallback). Include separate dev commands and a single production build/start path compatible with Replit Core. Use `PORT` provided by the host and listen on `0.0.0.0`.
>
> Add Pydantic settings for `DATABASE_URL`, `OPENAI_API_KEY`, `TAVILY_API_KEY`, `INGESTION_SECRET`, environment and optional model name. Validate key presence only on routes that need them so the public app works without keys; never print secrets. Configure SQLAlchemy and Alembic; create a small simple migration smoke table or implement health probes before full schema. Add `/api/health`, `/api/ready`, consistent error envelope, permissive local-dev CORS only (same-origin in prod), logging without PII, and safe API exception handling.
>
> Create initial Noka branded frontend shell with header, sidebar/top navigation on desktop and mobile, Home, Profile, Signals, Forecast, Matches, Roadmap, SDGs, and Model Lab as internal routes. Make polished light-theme responsive placeholders (not fake data cards). Create reusable PageHeader, GlassCard, EmptyState, ErrorState, LoadingSkeleton, EvidenceBadge, and SiteFooter. No dark-theme toggle in MVP.
>
> Add tests for API health, router navigation, and production frontend build; README instructions for running in Replit, secrets setup, migration, publish workflow, and how to verify the public `.replit.app` URL. Do not claim to actually publish if you cannot operate my Replit UI. Stop after this phase.

**Acceptance:** build and tests pass; `/`, `/profile`, `/forecast`, and `/api/health` load from one Replit web app. Publish it immediately and keep URL for later phases.
