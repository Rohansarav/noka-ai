# Noka public evidence register — Phase 2

## Software evidence addition — 21 October 2026

Software skills use the [O*NET 31.0 Software Skills dictionary](https://www.onetcenter.org/dictionary/31.0/csv/software_skills.html) and its [versioned CSV](https://www.onetcenter.org/dl_files/database/db_31_0_csv/software_skills.csv), published by USDOL/ETA and the National Center for O*NET Development under [CC BY 4.0](https://www.onetcenter.org/license_db.html). Retrieved file SHA-256: `6aabb96b464288db849580e6510530efff3f80e25dde2bb23f1fc36bb526b016`. The source records workplace software examples and hot/in-demand flags; it supplies no importance rating or proficiency threshold for these associations. Noka normalizes concept spelling, filters to supported occupations and provides explicitly identified search aliases. Associations do not imply broad-skill mastery, mandatory tool checklists, Malaysian demand or endorsement. The 13-row software fixture is an attributed subset of this exact source; importer tests retain its parent checksum. Original files remain outside the repository in the ignored public cache.

Verified on 20 October 2026 (Asia/Kuala_Lumpur). The importer stores original URLs, publisher, version, SHA-256, retrieval timestamp, licensing/terms, geography, granularity and publication date when known. Public downloads live in ignored `data/raw/`, not the frontend bundle. `data/raw/manifest.json` records each actual retrieval. The database source rows expose this lineage through `/api/datasets/summary` and `/api/sdgs`.

## Indeed Hiring Lab: US occupational-sector posting indices

- Canonical repository: https://github.com/hiring-lab/job_postings_tracker
- Verified branch: `master`; pinned repository commit: `554e4673d0b9a9fd64d4b0da354e5bb5e112beda`.
- Exact file: `US/job_postings_by_sector_US.csv`.
- Immutable file URL: https://raw.githubusercontent.com/hiring-lab/job_postings_tracker/554e4673d0b9a9fd64d4b0da354e5bb5e112beda/US/job_postings_by_sector_US.csv
- SHA-256: `11501409680563c03e6d321e42283cbb894d74d5a58c5de8c2a1a94b7989096a`.
- Licence: Creative Commons Attribution 4.0 International. [Pinned licence](https://raw.githubusercontent.com/hiring-lab/job_postings_tracker/554e4673d0b9a9fd64d4b0da354e5bb5e112beda/LICENSE); [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Attribution: Indeed Hiring Lab, Job Postings Index. Noka selects US **total postings**, reorders rows by sector/date and stores source lineage; it does not alter the index values.
- Verified frequency: **daily**. Every one of the 47 total-posting series in this snapshot has 2,443 consecutive dates, **2020-02-01 through 2026-10-09**. The publisher describes weekly refreshes; this Noka implementation refreshes only through explicit CLI imports, never silently or on a schedule.
- Raw rows: **229,642** across `total postings` and `new postings`. Imported observations: **114,821 total-posting rows**; new-posting rows are validated but intentionally excluded, not mixed into the same key.
- Original release/publication date: not supplied in the CSV; stored **null**. Git version and actual download time do not imply an original publication date.

### Exact verified CSV schema

| Column | Observed example | Noka interpretation |
|---|---|---|
| `date` | `2020-02-01` | ISO observation date |
| `jobcountry` | `US` | ISO alpha-2 country; other countries rejected |
| `indeed_job_postings_index` | `100` | Finite, non-negative numeric index |
| `variable` | `total postings`, `new postings` | Import only total; reject unexpected categories |
| `display_name` | `Accounting`, `Software Development` | Indeed occupational-sector label |

The source methodology describes seasonally adjusted series using a **seven-day trailing average**, with **2020-02-01 = 100**. A value of 101 represents 1% above baseline. The README dictionary loosely calls this “% change”; Noka follows its explicit index interpretation and the verified baseline rows, rather than subtracting 100 or relabelling indices as counts. `adjusted_flag=true` is based on the documented sector methodology, not an invented CSV column. No separate unadjusted sector series is imported.

Limitations: Indeed sectors are normalized job-title groupings, not interchangeable with industries, O*NET occupations or skills. US is not Malaysia. Index levels are not posting counts, salaries, probabilities or future demand. Historical values can be revised (including a documented methodology change in November 2024). This latest-vintage snapshot cannot establish a time-valid historical forecast backtest. No forecasts are trained in Phase 2.

## O*NET® 31.0 Database: real occupations and skill mappings

- Discovery/current release: https://www.onetcenter.org/database.html (verified 31.0 at retrieval).
- Licence/attribution rules: https://www.onetcenter.org/license_db.html — **CC BY 4.0** for the downloadable database files.
- Original publisher: U.S. Department of Labor, Employment and Training Administration (USDOL/ETA); developed by the National Center for O*NET Development.
- Exact files discovered on the release page:
  - https://www.onetcenter.org/dl_files/database/db_31_0_csv/occupation_data.csv
  - https://www.onetcenter.org/dl_files/database/db_31_0_csv/essential_skills.csv
  - https://www.onetcenter.org/dl_files/database/db_31_0_csv/transferable_skills.csv
- File retrieval timestamps/checksums are stored per source. Release version is `31.0`; an exact original release date was not independently established, so `publication_date` remains null. Rating-row `Date` values are collection/review metadata, not the database's release date.

### Exact verified schemas and selection

`occupation_data.csv`: `O*NET-SOC Code`, `Title`, `Description` (1,016 occupations in the retrieved source; only the curated 25 are imported).

Both skill files have these 16 columns: `O*NET-SOC Code`, `Title`, `Element ID`, `Element Name`, `Scale ID`, `Scale Name`, `Data Value`, `N`, `Standard Error`, `Lower CI Bound`, `Upper CI Bound`, `Recommend Suppress`, `Not Relevant`, `Date`, `Domain Source`.

Noka selects `Scale ID=IM` (importance, original **1–5** scale) for the 25 curated occupations, rejecting missing/non-finite/out-of-range ratings and excluding `Recommend Suppress=Y`. Level (`LV`) rows are not mixed with importance. The release provides 18,200 essential and 45,500 transferable skill rows overall; Noka imports **35 canonical skill elements** and **875 occupation–skill ratings**. Aliases are empty arrays because no verified alias dataset was imported. Category is `essential` or `transferable`, based on the original file. Importance is not an employment probability, match percentage or a demand forecast.

The catalogue uses exact source titles/descriptions and source occupation codes. The **role → Indeed sector crosswalk is Noka judgement**, not an official O*NET or Indeed crosswalk. It is reviewed in [CURATION_REVIEW.md](CURATION_REVIEW.md) and versioned in `data/curation/catalogue.json`. The project owner explicitly approved these proposals in this chat on 20 October 2026. Twenty-three roles have sector proxies; environmental engineers and sustainability specialists remain uncovered rather than receiving a misleading substitute series. **Every role has `individual_statistically_forecastable=false`, including those with sector evidence.**

Required attribution: This application includes information from the O*NET® 31.0 Database by USDOL/ETA, used under CC BY 4.0. Noka has selected records and added crosswalks and SDG links. USDOL/ETA has not approved, endorsed, or tested these modifications. O*NET® is a trademark of USDOL/ETA. No official logos are reused.

## United Nations: all 17 SDGs and 169 official targets

- Official goal explorer: https://sdgs.un.org/goals
- Exact official API URL: https://unstats.un.org/SDGAPI/v1/sdg/Goal/List?includechildren=true
- API documentation: https://unstats.un.org/SDGAPI/swagger/
- Publisher: United Nations Statistics Division.
- Shape: list of 17 objects, each containing `code`, `title`, `description`, `uri`, `targets`; target objects contain `code`, `title`, `description`, `uri` and nested indicators/series. Noka imports goal code/title/description and target code/**title** as the official target wording. Nested indicator measurements, series and release metadata are not imported. Strict checks require 17 unique goals and 169 unique, correctly parented targets.
- The original 2030 Agenda was adopted **2015-09-25**; stored as the original document date, clearly separate from the current API snapshot's retrieval time/checksum. For example, target 4.4 was cross-checked against https://sdgs.un.org/goals/goal4. All target descriptions come from the official API, not search snippets or model memory.
- Terms: https://www.un.org/en/about-us/terms-of-use. No CC/open-data licence is asserted for the UN wording. The source remains an attributed official-reference import subject to UN terms; verify additional redistribution permissions before commercial reuse. Direct access to the general UN terms page was restricted during verification, so no broader permission is inferred.
- Seven reviewed contextual links connect five occupations and two skills to official targets, with per-link rationale, source, reviewer and review timestamp. They describe applicability, not measured impact. All goals/targets remain visible even where no role/skill links exist.
- The content of this publication has not been approved by the United Nations and does not reflect the views of the United Nations or its officials or Member States. Noka uses no official UN emblems or SDG logo/icon artwork.

## World Economic Forum: structural context, not numeric predictions

- Canonical report page: https://www.weforum.org/publications/the-future-of-jobs-report-2025/
- Official report PDF: https://reports.weforum.org/docs/WEF_Future_of_Jobs_Report_2025.pdf
- Publisher/date: World Economic Forum, **2025-01-07**.
- Direct automated retrieval of the report webpage was restricted. The official PDF was successfully downloaded (18,604,420 bytes), verified as PDF, and hashed: `f25987c0dee6eba2d832f80924b0e926a4705605cbd6a5c5f10323897da31271`. Retrieval evidence is in `data/curation/wef_source.json`; the copyrighted full PDF is not committed or redistributed.
- Four short, attributed editorial paraphrases are stored in the reviewed catalogue: technology-role growth context, AI/data/cybersecurity skill importance, and analytical thinking. Their status records the project-owner review; they do not contain fabricated numeric forecasts or map WEF global employer-survey expectations into individual US/Malaysian employment predictions.
- Horizon/geography: qualitative **2025–2030 global employer-survey context**, entirely separate from the US daily historical indices and any future four-week statistical model.
- Terms: https://www.weforum.org/about/privacy-and-terms-of-use/. WEF copyright retained; only short attributed paraphrases are stored. No open licence is claimed. The CLI imports these source-controlled reviewed records and verified PDF provenance; it does not scrape or re-download the entire report on every data refresh.

## Import controls, fixtures and failure behavior

`scripts/import_data.py` supports online download, `--dry-run` and `--offline --directory <path>`. Offline input must have the expected official URLs and matching SHA-256 manifest; unverified files, schema drift, conflicting duplicates, missing indices, unknown countries/sectors or broken curation references fail explicitly. Dry-run validates the full bundle but writes **nothing to the database**, including no ingestion-run row. Online dry-run may write downloaded files/manifest to its cache directory.

Native PostgreSQL/SQLite upserts use stable entity/natural keys. Dataset writes and successful-run entries share one transaction. On failure, rollback preserves last-successful records; a separate failure audit row is stored (except in dry-run). Logs include public file names, sizes/checksums, row counts, batch progress, date ranges and error class; they do not print connection strings, SQL values, secrets or resume content. Imports require explicit CLI execution; no public endpoint triggers ingestion. Human review is bound to a content fingerprint: later edits to crosswalks, SDG rationales or WEF summaries cannot silently inherit an earlier approval.

`data/fixtures/` is an explicitly identified **real-row subset**, not demo/synthetic data: 282 original Indeed CSV rows (141 total + 141 new) from 2020-02-01..03 across all 47 sectors; the 25 source occupation rows; their 875 IM skill rows; official 17 goals/169 targets with indicator descendants removed; source licence/readme evidence; and derived API responses used only in tests. The manifest records actual original URLs, upstream parent checksums, retrieval times, subset checksums and transformations. Fixture imports visibly mark their source notes as **REAL-ROW FIXTURE SUBSET**. Never represent this three-day subset as the full historical dataset. Full raw downloads are ignored by Git.

No Malaysian historical observations, simulated market values, trained forecasts, evaluations, fake salaries or posting counts are included. Original CSS artwork and lucide-react icons remain from earlier phases; frontend/backend libraries retain their upstream licences.
