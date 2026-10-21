# NOKA — premium UI/UX overhaul

Verified in the actual running React/FastAPI application on 21 October 2026. This extends checkpoint `ebdd80f` on `feat/integrated-future`. The final UI commit is recorded in the companion delivery manifest.

## Design transformation

My Future now opens with the interactive Career Universe as its dominant element. The previous long introduction and five repeated role cards have been removed from that composition. A global World Dial, a contextual Ask Noka dock, and a short Future Self strip form one connected experience. The original React Flow engine and authoritative graph remain intact.

The light identity now uses warm off-white, mint and sky-blue surfaces, restrained gradients, fine dividers, quieter navigation, and an editorial serif accent. Supplementary sources, methods, conversations and limitations are disclosed on demand. The visual redesign changes frontend composition and interaction; it does not alter forecasts, matching algorithms, review approvals, ownership or private API protections.

## Main screens redesigned

| Screen | New focal point and actual interaction |
|---|---|
| My Future / Career Universe | Large real graph, compact connection filters and role selector, contextual companion tabs, scenario annotations and expandable exploration. Short Future Self summary with the full personalized story available on demand. |
| World Dial | One global, three-position scenario selector. Distinct selected treatments and meaningful priority/narrative changes; no invented skill-fit score changes. |
| Ask Noka | Branded compass, suggested questions, a compact composer, concise readable response sections and contextual follow-ups. Tool names, execution IDs and events live in a collapsed activity drawer. Genuine request state drives animation; there are no artificial waits. |
| Intelligence Radar | Source-backed trend rows with expandable evidence; a research index and focused source reader replace the long card wall. Market filters, dates, uncertainty and pending mappings remain accessible. |
| My Pathway | A connected milestone timeline with a study-hours control, immediate schedule preview, collapsible practice/project details, saved progress and private learning notes. |
| My Impact | Interactive career → skill/responsibility → specific SDG target stage. Selecting a relationship reveals the target and its review state; original evidence is one disclosure away. |
| Model Lab / shared shell | Consistent typography, lighter audit sections, retained actual forecast controls/results and methodology. Shared loading states use an accessible compass driven by real pending work. |

Mobile has a compact horizontal dial, shortened filter labels with full accessible names, a readable selected-node camera, a compact composer, horizontally browsable prompts/research, and a compact role/hour commitment layout. Tablet retains the map/companion split. These are deliberate responsive compositions, rather than a vertical copy of every desktop panel.

## Interactions verified

Actual browser checks, using the existing clearly labelled demo profile:

- Switched between Governed AI, Acceleration and Human-AI Collaboration. Skill-fit values stayed identical; scenario priorities, annotations and Future Self summaries changed. In a direct check after panning, the camera stayed at `translate(88.46px, 156.39px) scale(0.62)` through the world change.
- Panned the real React Flow graph from `translate(23.46px, 111.39px) scale(0.62)` to `translate(88.46px, 156.39px) scale(0.62)`. Expanded exploration, Focus and keyboard Escape exit worked; exit restored focus to the expand control. Zoom increased the actual camera scale from .62 to .744; Fit remained functional.
- Changed study hours by keyboard: at two hours/week, the 24-hour first milestone occupied weeks 1–12; at 40 hours/week, it occupied week 1. Preview did not silently persist a change. The saved 12-hour commitment and existing completed milestone remained intact after navigation/reload.
- Read a source-backed declining accountant outlook, expanded its evidence and filtered research to Malaysia. The source reader retained original references and dates; missing dates stayed explicitly unverified.
- Explored Registered Nurses → Instructing → target 4.4 and opened its evidence. The original reviewed relationship displayed Human reviewed. Selecting target 3.8 displayed Pending review; no approval was created.
- Submitted an actual Ask Noka question: “How does this role change across the three worlds?” The real provider execution completed with one `get_future_context` tool call and four recorded events. Reopened it from saved history, inspected the activity drawer, and verified the concise response and follow-up actions. No synthetic activity was substituted.
- Checked desktop 1440 × 1000, mobile 390 × 844, and tablet 768 × 1024. Corresponding document client/scroll widths were 1425/1425, 375/375 and 753/753: no horizontal document overflow. Mobile navigation focused its first link and closed on selection.
- Visually inspected the actual rendered screens and saved captures. Fixed issues found during inspection: tiny whole-map mobile fit, missing accessible name on icon-only expansion, ambiguous repeated Impact relationship labels, disabled-button contrast, excessive header spacing, and a narrow Future Self text column. No browser console errors were returned in the final check.

Purposeful motion is limited to real state: scenario surfaces/annotations, entering milestone details, actual waiting compass and genuine answer arrival. Reduced-motion preferences disable these animations/transitions. Companion tabs support arrow-key selection; expansion has a focus loop and Escape exit. Sources and longer explanations remain available through keyboard-accessible native disclosures.

## Test/build results

All final checks passed:

| Command | Observed result |
|---|---|
| `pnpm typecheck` | Passed. The final production build also ran TypeScript checking against the final sources. |
| `pnpm build` | Passed: TypeScript + Vite; 1,826 modules transformed. |
| `pnpm exec vitest run --config frontend/vite.config.ts --reporter=json --outputFile=../docs/qa/premium-vitest.json` | **76 passed, zero failed**. |
| `git diff --check` | Passed. |
| Actual browser inspection | Completed on desktop, mobile and tablet; real Guide execution and preserved evidence interactions checked. |

The frontend suite increased from 72 to 76 tests. New meaningful coverage verifies prompt selection without provider traffic, companion keyboard tabs/expansion focus, interactive SDG target/review selection, and market/source disclosure behavior. Existing tests were updated for intentional copy and composition changes while preserving their behavioral checks. One intermediate assertion expected the word “unavailable” while the authoritative error said “not configured”; it was corrected. The final suite has no failing tests.

The backend was not changed in this UI task. Its prior 89-test result is historical evidence, not a newly executed backend suite for this task. Actual browser API/provider traffic was exercised against the running service.

## Remaining design problems and limits

- A whole dense graph cannot be legible simultaneously on a phone. The selected real node now opens at readable zoom; users pan or zoom out for the wider network, or use the accessible list.
- Long canonical occupation names and official target wording are retained. They wrap in narrow layouts; substantive official target text is not rewritten merely to make it shorter.
- Long companion answers can scroll inside the desktop dock. The concise default response and activity disclosure reduce density, but a future user study could refine the dock's ideal height.
- Responsive and keyboard checks are local evidence, not a formal WCAG audit, screen-reader certification or physical-device test matrix. Reduced motion is implemented in CSS and camera behavior; an OS preference toggle was not part of this browser run.
- Remote database/provider latency still affects initial loads. Genuine loading states communicate waiting; no cosmetic delay or fake progress is added.
- Replit publication remains on hold under the owner's existing instruction. No deployment was performed or public URL claimed. Existing pending SDG/source reviews and forecast limitations remain unchanged.

## Run and review

The updated application is running at [Open NOKA](http://127.0.0.1:8010/). Refresh an older open tab to load the latest compiled frontend.

From the existing repository, after locked dependencies and configured server-side environment:

```powershell
pnpm build
$env:PORT = '8010'
uv run python scripts/start.py
```

No new database migration or frontend secret is required for this overhaul. The final source archive excludes `.env`, private database contents, dependencies and virtual environments.

Primary implementation files: `FuturePages.tsx`, `OutlookExplorer.tsx`, `premium.css`, `components.tsx`, `App.tsx`, `main.tsx`, and the Career Universe/Graph/Detail/AgentActivity components. The companion tests and sanitized QA JSON are included in the source checkpoint.

## Actual screenshots

Open `Noka-Premium-Gallery.html` for the complete gallery. Every capture is from the running application, not a mockup. Some captures are full-page and tall.

### My Future · Collaboration

![My Future · Collaboration](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/premium-screenshots/my-future-collaboration.jpg)

### World Dial · Acceleration

![World Dial · Acceleration](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/premium-screenshots/my-future-acceleration.jpg)

### World Dial · Governed AI

![World Dial · Governed AI](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/premium-screenshots/my-future-governed.jpg)

### Expanded Career Universe

![Expanded Career Universe](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/premium-screenshots/career-universe-expanded.jpg)

### Intelligence Radar

![Intelligence Radar](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/premium-screenshots/intelligence-radar.jpg)

### My Pathway

![My Pathway](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/premium-screenshots/my-pathway.jpg)

### My Impact · Instructing to target 4.4

![My Impact · Instructing to target 4.4](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/premium-screenshots/my-impact.jpg)

### Ask Noka · actual recorded activity

![Ask Noka · actual recorded activity](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/premium-screenshots/ask-noka-activity.jpg)

### Mobile · readable role focus

![Mobile · readable role focus](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/premium-screenshots/mobile-my-future.jpg)

### Mobile · compact companion and future story

![Mobile · compact companion and future story](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/premium-screenshots/mobile-ask-noka.jpg)

### Tablet workspace

![Tablet workspace](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/premium-screenshots/tablet-my-future.jpg)

### Model Lab

![Model Lab](C:/Users/Rohan/Documents/Codex/2026-10-20/files-pasted-by-the-user-noka/outputs/premium-screenshots/model-lab.jpg)

