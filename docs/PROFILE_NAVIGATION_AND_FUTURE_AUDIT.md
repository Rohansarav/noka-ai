# Profile navigation fix and My Future audit

21 October 2026. Scope: fix item 1; inspect and explain items 2 and 3. Career catalogue, matching scores and graph selection rules are unchanged by this patch.

## 1. Editing without repeated extraction — fixed

The progress labels in `frontend/src/Onboarding.tsx` were static list items. The About You continuation was coupled to `begin()`, whose only bypass depended on manual mode, empty text and existing skills. Selecting upload mode or typing experience therefore required extraction to move forward through that control. Even the bypass validated background fields before allowing skill review.

The three progress steps are now accessible buttons. Existing profiles can open Your Skills directly, and Your Direction when at least three skills are reviewed. A separate Review my skills / Continue with saved skills button works from either input method, including when a PDF is selected or manual text is present. Those transitions persist structured drafts and make no `/analysis`, `/resume` or OpenAI request. Entered text and the selected file remain in component memory when changing steps. Only the explicit Analyse my experience button requests analysis. New profiles retain initial analysis gating, and returning from a review step does not repeat analysis or discard its in-memory suggestions.

Step movement does not immediately replace the confirmed skills used by My Future: the existing Explore My Future action still commits the reviewed profile. Source text remains transient and is not written into drafts.

Changed files: `frontend/src/Onboarding.tsx`, `frontend/src/onboarding.css`, `frontend/src/ProfilePages.test.tsx`. No backend, migration, dependency or API contract change.

Verification: 14 profile tests pass, including new tests for direct step navigation with a selected PDF, optional manual text with explicit-only analysis, and new-profile gating without repeated extraction. Commands: `pnpm test frontend/src/ProfilePages.test.tsx`; `pnpm test --reporter=json --outputFile=../docs/qa/profile-navigation-vitest.json` (95 tests pass); `pnpm build` (passes, including TypeScript). The JSON run is retained in `docs/qa/profile-navigation-vitest.json`. No screenshots were taken, as requested. Backend tests were not repeated for this frontend-only change; the prior backend run was 102 passing tests.

## 2. Where career interests come from

The full chain is:

`data/curation/catalogue.json` selected occupation codes → `backend/app/ingestion/runner.py` → `parse_onet()` in `backend/app/ingestion/parsers.py` → SQL `Role` records → `/api/roles` in `backend/app/evidence_api.py` → `useCatalogue()` in `frontend/src/ProfilePages.tsx` → checkbox list in `Onboarding.tsx`.

The choices are not literal frontend template titles. However, the catalogue is explicitly curated to a small fixed selection. The current local database was checked directly: **25 roles, 35 skills and 875 role-skill mappings**. The importer rejects catalogues outside **20–30 unique occupations**, so importing a wider catalogue requires changing that validation, not just adding a search box. Titles and descriptions are imported from O*NET occupation data; the selection and sector crosswalk are Noka curation. Requirement links use the original importance scale, skip suppressed ratings and retain source identifiers.

Examples of current roles: Software Developers, Data Scientists, Information Security Analysts, Computer Systems Analysts, Mechanical Engineers, Registered Nurses and Sustainability Specialists. A specific interest such as Machine Learning Engineer or AI Product Manager is not a separate selectable role in this catalogue. Search alone would not create the missing roles or their requirement evidence.

Users can choose at most five catalogue IDs. The backend rejects IDs outside the Role table. There is no custom career-title input/resolution contract. The free-text goal is saved, but is not parsed into career interests or used in deterministic ranking. Interests currently add **5 points** to a selected role only if its weighted skill coverage is above zero. A selected career can still fall outside the five displayed matches. Selecting an interest does not guarantee a visible exploration path to that role.

Recommended next design, not implemented in this patch:

1. Expand the source-backed occupation catalogue and replace the fixed chip wall with searchable, paginated titles, aliases and career families. Adjust the 20–30 import cap and separate occupation coverage from optional sector-forecast crosswalks; a role without a defensible sector proxy should not be excluded merely for that reason.
2. Store the user's exact desired title separately from canonical occupation IDs, with mappings, provenance and a confirmed/ambiguous/unmapped status. For example, “ML Engineer” may connect to more than one existing occupation; show the proposed interpretation and let the user confirm it. Do not manufacture an occupational requirement profile or local demand claim for a custom title.
3. Allow explicit target-career exploration even when that role is outside the highest-fit results. Keep current readiness and stated aspiration visible as separate concepts, rather than burying aspiration in a small score bonus.
4. If goals will influence analysis, extract a bounded structured goal/context model and explicitly wire its fields into retrieval, ranking or explanation with tests. Simply storing a goal or sending it to an LLM does not make matching context aware.

## 3. What Possible Direction means

`backend/app/matching.py` is the authoritative matcher. It requires a confirmed profile with at least three skills. It uses role-skill importance values of at least **3/5** and converts self-ratings as follows: Learning = **0.25**, Working = **0.65**, Strong = **1.0**, absent skill = **0**.

For each role:

`coverage = sum(importance × self-rated level) / sum(importance)`

`displayed score = min(100, coverage × 100 + selected-interest bonus)`

The bonus is 5 when the role is selected and coverage is positive; otherwise 0. Results are sorted by score, then title and ID, and truncated to five. `backend/app/career_graph.py` converts those results into role nodes; `frontend/src/universe/CareerNodes.tsx` labels every role node POSSIBLE DIRECTION. This label is a UI type label, not an independently reasoned or verified career outcome.

Example with three equally important requirements: one Strong, one Working and one absent gives `(1 + .65 + 0) / 3 = 55%` weighted coverage; selecting that career gives a displayed score of 60. This is a heuristic index, not a 60% hiring probability. The displayed score includes the preference bonus even though the node calls it “skill fit”; pure coverage is available separately.

The World Dial applies a second deterministic rule in `backend/app/future.py::ranked()`: **planning index = displayed score + sum(max(0, importance − 3))** for that world's named skills. It reorders only the original five, so a role ranked sixth cannot enter through a scenario change. The scenario lists are authored assumptions: acceleration uses Programming/Technology Design/Systems Analysis; governed uses Monitoring/Quality Control Analysis/Judgment and Decision Making; collaboration uses Active Learning/Coordination/Critical Thinking/Active Listening. The added emphasis depends on the role requirements, not the user's proficiency deficit. It does not change source importance values or the displayed base score.

Inputs actually affecting outputs:

| Input | Current use |
|---|---|
| Confirmed canonical skills and self-rated levels | Weighted coverage and gaps |
| Selected catalogue interests | Conditional +5 bonus |
| World Dial | Planning order within the existing top five; pathway priority |
| Weekly learning hours | Pathway scheduling, not role fit |
| Completed learning tasks | Pathway schedule/progress; no automatic skill proficiency upgrade |
| Current field, employment status, free-text goal | Stored profile context; not consumed by matcher |
| Overall experience years / years per skill | Stored; not scored |
| Country / market | Preference and disclosure; no local vacancy or Malaysian requirement adjustment |
| Forecasts and research feeds | Separate evidence/context; not inputs to this skill-fit score |

The Guide's `get_current_profile` tool exposes country, interests and workspace context but does not currently expose the onboarding goal/background fields. Even conversational personalization does not automatically consume every field the user entered.

## 4. What Skill to Build means

The matcher records every important requirement whose self-rating is below Strong. `gap = 1 − level`, giving absent = 1.0, Learning = .75, Working = .35, Strong = 0. Importance at least 4/5 marks a critical gap.

The graph takes the **first three gaps per displayed role**, sorted by importance descending and then skill name. It combines those canonical skill IDs across all five roles. A skill the user has not selected becomes a `required_skill` node labelled SKILL TO BUILD; a selected skill remains MY SKILL, even if Learning or Working leaves a deficit for a role. Consequently a skill can be a priority gap on an edge without being labelled Skill to Build on its node. All confirmed skills are included as owned nodes regardless of whether the five roles require them.

The graph selects its three gaps by importance, not by `importance × gap`. For example, a Working skill with importance 4.5 has weighted deficit 1.575, while an absent skill of importance 4 has deficit 4. The current graph can prioritize the first one because 4.5 is greater than 4. This explains why high-importance general skills can repeatedly appear and why the graph can miss a more substantial practical deficit.

My Pathway uses a different rule: scenario-named gaps first, then `importance × gap` descending. Graph priority selection does not use that ordering. Scenario highlights show above-threshold requirements for the selected role and can include skills already mastered; they indicate emphasis, not necessarily a missing skill. Repeated nodes are deduplicated by canonical ID, with relationships retained per role.

Recommended next matching changes, not implemented here: rank the complete eligible catalogue before choosing a display subset; keep aspiration and readiness separate; expose each score component; use one role-specific gap priority function across graph and pathway; prioritize supported deficits rather than high importance alone; distinguish missing from developing skills; and add source-backed task/tool/specialty requirements before claiming specialty-level fit. Evaluate ranking against reviewed example profiles and expected target/gap sets. Self-rated broad skills and arbitrary weights are not a validated assessment of employability.

## Runtime and deployment

The local application is rebuilt and served on port 8010. No provider request was required for this fix or its navigation tests. Replit publishing remains on the owner's existing hold. Nothing was published and no profile was deleted.
