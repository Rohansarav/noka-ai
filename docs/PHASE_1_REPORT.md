# Phase 1 — Visual system and dashboard shell

Date: 20 October 2026 (Asia/Kuala_Lumpur). Scope: Phase 1 only.

## Result

Implemented the light-only visual system and responsive dashboard on the Phase 0 architecture. No integrations or user-data persistence were added. Local production service runs at http://localhost:8000; gallery at http://localhost:8000/design-preview.

- Central CSS variables for cream, mint, aqua, powder blue, dark ink, primary/action colours, chart palette, gradients, radii, shadows and 180–240ms motion. Action blue is darker than decorative primary blue to support readable white labels.
- Noka hero, tagline, Build My Future action, Scout / Oracle / Guide steps, module links, no-profile tile and separate intelligence status. Source ingestion is explicitly disconnected: no data, no successful refresh, no invented dates or metrics. API connectivity is shown separately.
- `/profile`, `/matches`, `/roadmap` say “No profile yet” and link to `/profile/intake`. Intake is a clearly labelled, non-collecting preview; resume/manual-entry controls are disabled until a later phase.
- `/design-preview`: typography, colour tokens, badges, native labelled progress, gradients, chart palette with names and line patterns, empty/loading/error samples, and a sample notification which explicitly says nothing was saved.
- Dismissible polite live-region notifications, eight-second timeout paused on hover/focus, reduced-motion support, visible keyboard focus, route-to-main focus, mobile navigation first-link focus and Escape-to-toggle behavior. Selecting even the current page closes the mobile disclosure.

## Files changed

- `AGENTS.md`: advance the authorized scope to Phase 1.
- `package.json`: explicit typecheck command; dependencies/locks unchanged.
- `frontend/src/App.tsx`: dashboard, module/intake routes and accessible navigation.
- `frontend/src/components.tsx`: consistent controls, badges, progress and states.
- `frontend/src/style.css`: centralized tokens and responsive visual system.
- New `frontend/src/DesignPreview.tsx`, `frontend/src/toasts.tsx`, `frontend/src/vite-env.d.ts`.
- `frontend/src/App.test.tsx`, `frontend/src/test-setup.ts`, new `frontend/src/design.test.ts`: behavior and contrast coverage.
- `backend/tests/test_api.py`: verify new SPA deep links use the same FastAPI server.
- `README.md`: current scope, typecheck and visual QA instructions.
- This report and `docs/qa/`: browser screenshots and measured responsive results.

## Commands and results

Commands run from repository root. This machine's pnpm command is `C:\Users\Rohan\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd`; installed Python environment is `.venv\Scripts\python.exe`.

```powershell
pnpm typecheck
pnpm build
pnpm test
.\.venv\Scripts\python.exe -m pytest -q
$env:ENVIRONMENT='production'; .\.venv\Scripts\python.exe scripts/start.py
git diff --check
```

- TypeScript typecheck: passed.
- Production Vite build: passed. FastAPI continues to serve its compiled assets and SPA fallback.
- Vitest: **40 passed**, including 19 WCAG contrast checks (normal text ≥4.5:1, chart strokes ≥3:1), honest feed status despite a healthy API, intake navigation, all module routes, menu focus/Escape/current-page close, gallery examples and toast dismissal/pause behavior.
- pytest: **12 passed**. One existing upstream Starlette test-client deprecation warning remains; no test failures.
- Live HTTP requests to `/`, `/profile`, `/forecast`, `/design-preview`, `/profile/intake`, `/api/health`, `/api/ready`: all **HTTP 200** from port 8000. No backend implementation or deployment configuration changes.
- Initial contrast-test asset loading failed under the CSS test transform; resolved by reading the actual CSS source through Node filesystem APIs. All final checks passed.

## Responsive and browser QA

Browser access was initially blocked by automatic browser security review. After the user restored access, verification proceeded in the supported browser, with explicit viewport overrides reset afterward.

Checked `/`, `/design-preview`, `/profile`, `/profile/intake` at **375px, 768px and 1440px**. All 12 route/viewport combinations had one H1 and `document.scrollWidth === document.clientWidth` (no horizontal overflow). Native scrollbar width is excluded from available content width. Raw observations: [responsive-results.json](qa/responsive-results.json).

- 375px: mobile toggle, single-column step/dashboard/gallery/intake cards, two-column colour samples; hero action opens intake. Opened menu focuses Overview; Escape closes it and restores toggle focus. Client navigation focuses main. Intake actions remain disabled and say coming soon. Toast fits within viewport.
- 768px: persistent sidebar, single-column content/card stacking, readable hero.
- 1440px: hero illustration, three step cards, two dashboard columns, two gallery columns, six colour samples.
- Visual evidence: [375px home](qa/home-375.png), [768px home](qa/home-768.png), [1440px home](qa/home-1440.png), [1440px gallery](qa/gallery-1440.png), [375px toast](qa/gallery-toast-375.png).
- Reduced-motion overrides are implemented in CSS. Physical mobile-device and screen-reader testing were not performed.

## Deployment and blockers

Local application is running. Replit build/start arrangement and server routes are preserved. A GitHub remote is configured at `https://github.com/Rohansarav/noka-ai.git`; Phase 1 has not been pushed by this work. No public deployment was attempted or claimed in Phase 1, and no verified `.replit.app` URL is available in this chat. Replit publishing/verification remains outstanding. No API keys are needed for this phase. No new implementation blockers remain.

## Commit message

`feat: add Noka visual system and responsive dashboard shell`

Stopped after Phase 1. No resume ingestion, source refresh, forecasting or roadmap persistence is implemented.
