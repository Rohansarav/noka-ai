# Real public-source test subset

These are real, attributed rows, not fabricated demo observations. `manifest.json` records exact upstream URLs, actual retrieval times, source checksums, subset checksums and transformations. See `docs/DATA_SOURCES.md` for complete schema, licence/terms and limitations.

- Indeed: all 47 sectors, both variables, three dates (2020-02-01 through 2020-02-03), 282 CSV rows. Only 141 total-posting observations are imported.
- O*NET 31.0: 25 selected occupation rows and their 875 original importance (IM) mappings; no values edited. CC BY 4.0, USDOL/ETA; Noka added selection/crosswalk/SDG relevance. USDOL/ETA has not endorsed modifications.
- UN: 17 goals, 169 official targets; nested indicator/series data removed. Official reference text, UN terms of use; no open licence asserted.
- `api.json`: real-row API-shaped derivative for frontend tests, generated against this subset; its import-run timestamps belong to fixture creation, not a production refresh. All subset sources are labelled in their notes.
- Readme/licence files support attribution and parsing; WEF's full copyrighted report is not redistributed. Its independently verified PDF retrieval metadata lives in `data/curation/wef_source.json`.

To validate without writing database rows:

```sh
uv run python scripts/import_data.py --directory data/fixtures --offline --dry-run
```

Full production evidence must use `data/raw`, not this subset. Fixtures are intended for tests or an explicitly labelled offline fallback only.
