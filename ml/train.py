"""Reproducible direct-horizon evaluation. Run: uv run python -m ml.train."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor
from sqlalchemy import select
from backend.app.database import engine
from backend.app.models import DemandObservation

OUT = Path(__file__).parent / "artifacts"
HORIZONS = (4, 13, 26)


def features(series):
    """All features use observations available on or before the feature date."""
    frame = pd.DataFrame({"current": series})
    for lag in (1, 4, 13, 26, 52):
        frame[f"lag_{lag}"] = series.shift(lag)
    for window in (4, 13, 26):
        frame[f"mean_{window}"] = series.rolling(window).mean()
        frame[f"std_{window}"] = series.rolling(window).std()
    return frame


def metrics(actual, predicted, current):
    actual, predicted, current = map(np.asarray, (actual, predicted, current))
    errors = actual - predicted
    denominator = np.abs(actual) + np.abs(predicted)
    return {"mae": float(np.mean(np.abs(errors))), "rmse": float(np.sqrt(np.mean(errors ** 2))),
            "smape": float(np.mean(np.divide(200 * np.abs(errors), denominator,
                          out=np.zeros_like(errors), where=denominator != 0))),
            "directional_accuracy": float(np.mean(np.sign(actual-current) == np.sign(predicted-current))),
            "n": len(actual)}


def candidates():
    return {"ridge": make_pipeline(StandardScaler(), Ridge(alpha=10)),
            "xgboost": XGBRegressor(n_estimators=80, max_depth=3, learning_rate=.05,
                                   subsample=1, colsample_bytree=1, random_state=42, n_jobs=2)}


def train():
    OUT.mkdir(exist_ok=True)
    with engine.connect() as conn:
        data = pd.read_sql(select(DemandObservation), conn)
    data["date"] = pd.to_datetime(data["date"])
    # Do not blend adjusted and unadjusted observations.
    chosen = data[data.adjusted_flag == True].copy()
    if chosen.empty:
        raise ValueError("Seasonally adjusted observations required")
    audit = {"rows": len(data), "used_rows": len(chosen), "sectors": int(chosen.sector.nunique()),
             "start": str(chosen.date.min().date()), "end": str(chosen.date.max().date()),
             "duplicates": int(chosen.duplicated(["country", "sector", "date"]).sum()),
             "aggregation": "Mean of daily seasonally adjusted indices, Monday–Sunday; omit partial last week. Missing weeks remain missing; no interpolation.",
             "fingerprint": hashlib.sha256(chosen.sort_values(["sector","date"]).to_csv(index=False).encode()).hexdigest()}
    if audit["duplicates"]:
        raise ValueError("Duplicate observations require resolution")
    report = {"version": "oracle-direct-v1", "generated_at": datetime.now(timezone.utc).isoformat(),
              "market": "US", "unit": "Job-posting index, not job counts", "audit": audit,
              "validation": "Expanding windows; 5 selection origins and 3 later holdout origins, each spaced 4 weeks apart within its group. A horizon-length embargo ensures all selection labels mature by the first holdout origin. Training target date <= origin.",
              "limitations": ["Retrospective revised source vintage; historical revisions were not available.",
                             "Small and overlapping evaluation windows; errors are dependent.",
                             "US sectors are not Malaysian occupations or individual skills.",
                             "Empirical error bands are descriptive, not calibrated confidence intervals."],
              "sectors": [], "horizons": {}}
    pooled = {h: {m: [[], [], []] for m in ("naive", "ridge", "xgboost", "selected")} for h in HORIZONS}
    bundles = {}
    for sector, daily in chosen.groupby("sector"):
        series = daily.set_index("date").indexed_value.resample("W-SUN").mean()
        series = series[series.index <= daily.date.max()]
        x = features(series)
        for h in HORIZONS:
            y = series.shift(-h)
            valid = x.notna().all(axis=1) & y.notna()
            last_origin = len(series) - h - 1
            first_holdout = last_origin - 8
            last_selection = first_holdout - h
            origins = list(range(last_selection - 16, last_selection + 1, 4)) + list(range(first_holdout, last_origin + 1, 4))
            records = []
            for origin in origins:
                # Labels mature at origin, including only t+h <= origin.
                indices = np.arange(len(series))
                mask = valid & (indices + h <= origin)
                if mask.sum() < 100 or not valid.iloc[origin]:
                    continue
                models = candidates()
                preds = {"naive": float(series.iloc[origin])}
                for name, model in models.items():
                    model.fit(x.loc[mask], y.loc[mask])
                    preds[name] = max(0., float(model.predict(x.iloc[[origin]])[0]))
                records.append({"origin": str(series.index[origin].date()), "target_date": str(series.index[origin+h].date()),
                                "actual": float(y.iloc[origin]), "current": float(series.iloc[origin]), "predictions": preds})
            if len(records) < 8:
                continue
            selected = min(("naive", "ridge", "xgboost"), key=lambda m: np.mean([abs(r["actual"]-r["predictions"][m]) for r in records[:5]]))
            scores = {}
            for name in ("naive", "ridge", "xgboost", "selected"):
                target = selected if name == "selected" else name
                held = records[5:]
                args = ([r["actual"] for r in held], [r["predictions"][target] for r in held], [r["current"] for r in held])
                scores[name] = metrics(*args)
                for destination, values in zip(pooled[h][name], args):
                    destination.extend(values)
            current = float(series.iloc[-1])
            prediction = current
            if selected != "naive":
                model = candidates()[selected]
                model.fit(x.loc[valid], y.loc[valid])
                prediction = max(0., float(model.predict(x.iloc[[-1]])[0]))
                bundles[f"{sector}:{h}"] = model
            errors = [abs(r["actual"]-r["predictions"][selected]) for r in records[:5]]
            radius = float(np.quantile(errors, .8))
            report["sectors"].append({"sector": sector, "horizon_weeks": h, "model": selected,
                "observed_through": str(series.index[-1].date()), "forecast_date": str((series.index[-1]+pd.Timedelta(weeks=h)).date()),
                "current": current, "forecast": prediction, "historical_error_band": [max(0.,prediction-radius), prediction+radius],
                "band_method": "80th percentile absolute selection-window error; 5 origins; descriptive only",
                "metrics": scores, "backtests": records, "missing_weeks": int(series.isna().sum())})
    for h, model_scores in pooled.items():
        report["horizons"][str(h)] = {name: metrics(*args) for name, args in model_scores.items() if args[0]}
    # A deployment gate is distinct from the untouched evaluation reported above.
    report["deployment_policy"] = {}
    for h in HORIZONS:
        scores = report["horizons"][str(h)]
        use_baseline = scores["selected"]["mae"] >= scores["naive"]["mae"]
        report["deployment_policy"][str(h)] = "persistence: selected portfolio failed holdout gate" if use_baseline else "selection-window winners"
        if use_baseline:
            for row in report["sectors"]:
                if row["horizon_weeks"] != h:
                    continue
                row["validation_winner"] = row["model"]
                row["model"] = "naive"
                row["forecast"] = row["current"]
                radius = float(np.quantile([abs(r["actual"]-r["predictions"]["naive"]) for r in row["backtests"][:5]], .8))
                row["historical_error_band"] = [max(0., row["current"]-radius),row["current"]+radius]
    report["hyperparameters"] = {"seed":42, "ridge_alpha":10, "xgboost": candidates()["xgboost"].get_params()}
    report["hyperparameters"]["xgboost"]["missing"] = "NaN (XGBoost default)"
    (OUT/"evaluation.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    joblib.dump(bundles, OUT/"models.joblib")
    print(json.dumps({"audit": audit, "horizons": report["horizons"], "forecasts": len(report["sectors"])}, indent=2))


if __name__ == "__main__":
    train()
