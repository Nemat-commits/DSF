"""Smoke tests for the data, model and dashboard deliverables."""

import json

import joblib
import pandas as pd

from dsf.config import (FEATURE_COLUMNS, FIGURE_DIR, METRICS, MODEL_DIR,
                        MODELLING_SET, PREDICTIONS, RAW_LOG, REPORT_DIR, TARGET)
from dsf.dashboard_app import create_app
from dsf.features import build_features, split_chronologically
from dsf.generate_data import simulate_log, validate_log


def test_raw_log_schema_and_size():
    df = simulate_log()
    validate_log(df)
    assert list(df.columns) == ["date", "item_code", "slot", "stock_count", "restocked"]
    assert len(df) == 168
    assert df["item_code"].nunique() == 3
    assert df["slot"].nunique() == 4
    assert df["stock_count"].ge(0).all() and df["restocked"].ge(0).all()


def test_target_is_next_check():
    features = build_features(simulate_log())
    a = features[features["item_code"] == "ITEM-A"].sort_values(
        ["date", "slot_index"])
    assert a[TARGET].iloc[0] == a["stock_count"].iloc[1]
    assert a[TARGET].isna().sum() == 1  # final check has no successor
    assert set(FEATURE_COLUMNS).issubset(features.columns)


def test_chronological_split_and_metrics():
    features = build_features(simulate_log())
    train, test = split_chronologically(features, 4)
    assert train["date"].max() < test["date"].min()
    assert len(train) + len(test) == 165

    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    assert set(metrics["models"]) == {"linear_regression", "decision_tree",
                                      "random_forest"}
    assert metrics["best_model"] in metrics["models"]
    assert all(0 <= m["mae"] < 20 for m in metrics["models"].values())
    assert metrics["baseline_persistence"]["mae"] > 0


def test_saved_artifacts_exist():
    for name in ("linear_regression", "decision_tree", "random_forest", "best_model"):
        assert (MODEL_DIR / f"{name}.joblib").is_file()
        assert joblib.load(MODEL_DIR / f"{name}.joblib") is not None
    assert len(pd.read_csv(MODELLING_SET)) == 168
    assert len(pd.read_csv(PREDICTIONS)) == 45
    assert len(pd.read_csv(RAW_LOG)) == 168
    assert (REPORT_DIR / "DSC293_Shelf_Stock_Forecast_Report.pdf").stat().st_size > 10_000
    assert (REPORT_DIR / "DSC293_Shelf_Stock_Forecast_Slides.pptx").stat().st_size > 10_000
    assert (REPORT_DIR / "handwritten_notes_facsimile.pdf").stat().st_size > 5_000
    assert len(list(FIGURE_DIR.glob("*.png"))) >= 6


def test_dashboard_endpoints():
    client = create_app().test_client()
    assert client.get("/").status_code == 200
    assert client.get("/api/metrics").json["best_model"] == "random_forest"
    for model in ("linear_regression", "decision_tree", "random_forest",
                  "persistence"):
        r = client.get(f"/api/series?model={model}")
        assert r.status_code == 200 and len(r.json["points"]) > 100
    alerts = client.get("/api/alerts?threshold=20").json
    assert isinstance(alerts["alerts"], list)
    result = client.post("/api/predict", json={
        "item_code": "ITEM-B", "slot": "post_morning",
        "stock_count": 18, "restocked": 0, "model": "random_forest",
    })
    assert result.status_code == 200
    assert 0 <= result.json["predicted_remaining"] <= 100
