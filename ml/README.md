# Oracle direct-horizon forecasting

Run from the repository root:

```sh
uv sync --frozen
uv run alembic upgrade head
uv run python scripts/import_data.py --offline
uv run python -m ml.train
```

Use the full, verified Indeed source cache. `data/fixtures` is a tiny test subset and must not be substituted for training history. The current artifact uses 114,821 seasonally adjusted daily US sector index observations, 47 sectors, 2020-02-01 through 2026-10-09. No duplicate country/sector/date records were found. It does not forecast Malaysian occupations, individual skills, job counts or salaries.

`train.py` averages observed daily indices into Sunday-ended weeks and excludes the incomplete final week. Missing weeks remain missing, without interpolation. Features include current index, lags 1/4/13/26/52 and trailing means/standard deviations over 4/13/26 weeks. Every training label's target date is on or before its origin. Models are direct 4-, 13- and 26-week forecasts.

Each sector/horizon uses five expanding-window selection origins and three later holdout origins. Origins are four weeks apart within each group. The horizon-length embargo between groups ensures all labels used for model selection have matured at the first holdout origin. Models: persistence, standardized ridge (alpha 10), and XGBoost (80 trees, depth 3, learning rate .05, seed 42, two CPU threads). Selection minimizes selection-window MAE per sector/horizon. A separate deployment gate falls back to persistence at a whole horizon if its selected portfolio fails to improve aggregate holdout MAE. Holdout metrics report the portfolio before this gate, so the decision is transparent.

Artifacts: `artifacts/evaluation.json` contains the input fingerprint, dates, aggregation, hyperparameters, sector forecasts, every backtest origin/target/prediction, metrics and deployment policy. `artifacts/models.joblib` preserves fitted nonbaseline selection winners. Only load this trusted local artifact. The served forecasts are the derived, dated JSON output; production does not retrain on scenario changes.

Metrics: MAE and RMSE in index points; sMAPE is mean(200 × |actual − prediction| / (|actual| + |prediction|)), with zero for a zero denominator; directional accuracy compares signs of change from the origin. Persistence always predicts no change, so its directional accuracy is zero unless the target is exactly flat.

Limitations: only three holdout origins per sector/horizon, overlapping windows, dependent errors, and one revised historical vintage. The 80th percentile absolute selection-window error gives a descriptive range using only five errors; it is not a calibrated confidence interval. Reported improvements do not establish general future predictive skill. Dependency versions are pinned in `uv.lock`. All training is on CPU.
