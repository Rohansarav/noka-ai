# Profile analysis correction — 21 October 2026

The previous manual option skipped experience analysis. Free-form AI skill names could have no canonical options, while the review control required an option before adding them. Aliases could also produce repeated suggestions. These were functional problems in the input-to-analysis contract.

## Result

- Exactly two methods: upload a PDF/DOCX or enter experience manually. Manual entry has a required textarea, length guidance, field errors and retry support. Existing saved skills can still be reviewed without retyping experience.
- Both methods submit to the owned, CSRF-protected `/api/profiles/{id}/analysis` endpoint. Protected pypdf/DOCX parsing precedes the same sanitized Pydantic `AnalysisInput` text contract (20–20,000 characters). Legacy `/resume` remains compatible.
- The configured gpt-4.1-mini uses [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) with a Pydantic model and catalogue-constrained skill IDs. The server revalidates the response. Incomplete, refused or malformed outputs use an explicit local fallback. Evidence excerpts must occur in the source after whitespace normalization. Unsupported excerpts are excluded with a warning.
- Exact and alias mappings are preferred; model reasoning can propose broader catalogue skills. Duplicate canonical candidates are merged. No skill or proficiency is confirmed automatically.
- Skills use addable suggestion cards, source disclosures, searchable catalogue choices, remove buttons and Learning/Working/Strong controls. There are no per-skill dropdowns. Unmapped terms have a searchable resolution rather than a disabled confirmation dead end.
- Original resumes, raw manual experience and unconfirmed candidate evidence are not persisted in onboarding drafts. Confirmed canonical skills continue through the existing scoring and career graph pipeline. Profile ownership, privacy, sidebar order and saved workspace hours are preserved.

## Verification

- `.venv/Scripts/python.exe -m pytest backend/tests -q`: **102 passed**, with one existing Starlette/httpx deprecation warning.
- `pnpm test -- --run --reporter=json --outputFile=docs/qa/profile-analysis-vitest.json`: **92 passed**; JSON report retained.
- `pnpm build`: passed, including TypeScript compilation.
- `git diff --check`: passed. Local `/api/ready`: HTTP 200 after restarting the current build on port 8010.
- Regression coverage includes equivalent PDF, DOCX and manual analysis; schema-invalid IDs/extra fields; incomplete output; invented evidence and PDF line breaks; duplicate aliases; CSRF/ownership; manual errors; add/remove/re-add; provider errors with input retained; saved hours; and final canonical skill saving.
- A separate demo session uploaded `data/demo/demo_cv.docx` and used the real OpenAI provider. Supported suggestions were addable. Programming, Critical Thinking and Writing were confirmed; Programming level changes and removal/re-addition worked. Completing onboarding reached My Future with all three owned skills visible in the graph.
- A second isolated demo session entered manual experience and used real OpenAI on a 390px viewport. Programming, Writing and Coordination were addable. Manual short-text validation preserved the text and focused its error. The skills page had zero select controls and no horizontal overflow.
- Browser screenshots are in the chat output folder `outputs/profile-analysis-fix/`: `openai-skill-review-desktop.png`, `manual-validation-mobile.png`, and `manual-openai-skills-mobile.png`.

## Boundaries and deployment

Pydantic guarantees response structure and allowed identifiers, not perfect semantic judgement. Human review is still required. The current catalogue has 35 broad O*NET occupational skills; tool names such as Python can suggest Programming, rather than introducing unsupported standalone scoring dimensions. Alias hints are Noka mappings, not new O*NET factual equivalences.

pypdf extracts text; it does not OCR scanned pages. Image-only documents receive an actionable manual-entry error. Files remain bounded to 5 MB and protected parsing limits remain in place. Provider confidence is qualitative, not calibrated.

No package, environment variable or database migration was added. Existing locked pypdf, OpenAI and Pydantic dependencies serve the Replit startup path. Replit publication remains on the owner's existing hold; no public deployment is claimed. AI mapping proposals remain pending until a human confirms them in the product.

The original user tab was left intact because it contained a populated direction form. Test sessions used separate loopback origins and did not delete or overwrite the user's profile.
