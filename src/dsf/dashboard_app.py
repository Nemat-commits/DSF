"""Flask dashboard for the shelf stock forecast.

Run with:  PYTHONPATH=src .venv/bin/python -m dsf.dashboard_app
The server binds 0.0.0.0 so it is reachable through the Arena live preview.
"""

from __future__ import annotations

import argparse
import json

import joblib
import pandas as pd
from flask import Flask, jsonify, render_template, request, send_from_directory

from .config import (DASHBOARD_DIR, FIGURE_DIR, LOW_STOCK_THRESHOLD, METRICS,
                     MODEL_DIR, PROCESSED_DIR, RAW_LOG)
from .features import latest_snapshots, one_prediction_row

_MODEL_CACHE: dict = {}


def _load_model(name: str):
    if name not in _MODEL_CACHE:
        path = MODEL_DIR / (f"{name}.joblib" if name != "persistence" else "best_model.joblib")
        _MODEL_CACHE[name] = joblib.load(path)
    return _MODEL_CACHE[name]


def create_app() -> Flask:
    """Build the app; data and metrics are loaded once at startup."""
    app = Flask(__name__, template_folder=str(DASHBOARD_DIR / "templates"),
                static_folder=str(DASHBOARD_DIR / "static"))
    app.config["JSON_SORT_KEYS"] = False

    features = pd.read_csv(PROCESSED_DIR / "features_full.csv")
    predictions = pd.read_csv(PROCESSED_DIR / "test_predictions.csv")
    raw = pd.read_csv(RAW_LOG)
    with METRICS.open(encoding="utf-8") as fh:
        metrics = json.load(fh)
    snapshots = latest_snapshots(features)
    model_names = list(metrics["models"]) + ["persistence"]

    # One compact series per item: full observed history + out-of-sample
    # forecasts on the final four days.
    series = []
    for item in sorted(raw["item_code"].unique()):
        hist = features[features["item_code"] == item].sort_values(
            ["day_index", "slot_index"])
        for row in hist.itertuples(index=False):
            series.append({
                "date": row.date, "item": item, "slot": row.slot,
                "stock": int(row.stock_count), "restocked": int(row.restocked),
                "day": int(row.day_index),
                "forecast": None, "actual": None, "split": "observed",
            })
        test = predictions[predictions["item_code"] == item].sort_values("date")
        for row in test.itertuples(index=False):
            base = {
                "date": row.date, "item": item, "slot": row.slot,
                "stock": int(row.stock_count), "day": None,
                "actual": int(row.actual), "split": "held_out",
            }
            for model in model_names:
                value = (int(row.stock_count) if model == "persistence"
                         else float(getattr(row, model)))
                series.append({**base, "model": model, "forecast": value})

    @app.route("/")
    def index():
        return render_template("index.html", metrics=metrics,
                               model_names=model_names,
                               default_model=metrics["best_model"],
                               threshold=metrics["low_stock_threshold"],
                               figure_names=sorted(p.name for p in FIGURE_DIR.glob("*.png")))

    @app.route("/figures/<path:name>")
    def figures(name: str):
        return send_from_directory(FIGURE_DIR, name)

    @app.route("/api/metrics")
    def api_metrics():
        return jsonify(metrics)

    @app.route("/api/series")
    def api_series():
        model = request.args.get("model", metrics["best_model"])
        if model not in model_names:
            return jsonify({"error": "unknown model"}), 400
        rows = [r for r in series if r.get("model", model) == model]
        return jsonify({"model": model, "points": rows})

    @app.route("/api/alerts")
    def api_alerts():
        model = request.args.get("model", metrics["best_model"])
        threshold = request.args.get("threshold", default=LOW_STOCK_THRESHOLD, type=int)
        if model not in model_names:
            return jsonify({"error": "unknown model"}), 400
        test = predictions.copy()
        alerts = []
        for row in test.sort_values(["date", "item_code", "slot"]).itertuples(index=False):
            estimate = (float(row.stock_count) if model == "persistence"
                        else float(getattr(row, model)))
            if estimate < threshold:
                alerts.append({
                    "item": row.item_code,
                    "date": row.date,
                    "slot": row.slot,
                    "current_stock": int(row.stock_count),
                    "forecast": round(estimate, 1),
                    "threshold": threshold,
                    "message": f"Forecast {estimate:.1f} units at next check — "
                               f"below {threshold}-unit threshold",
                })
        alerts = list(reversed(alerts))[:8]
        return jsonify({"alerts": alerts, "threshold": threshold, "model": model})

    @app.route("/api/predict", methods=["POST"])
    def api_predict():
        payload = request.get_json(force=True) or {}
        item = str(payload.get("item_code", "ITEM-A"))
        slot = str(payload.get("slot", "pre_morning"))
        model = str(payload.get("model", metrics["best_model"]))
        if model == "persistence":
            return jsonify({"error": "persistence is a baseline; choose a trained model"}), 400
        template = snapshots[(snapshots["item_code"] == item) &
                             (snapshots["slot"] == slot)]
        if template.empty:
            return jsonify({"error": "unknown item/slot combination"}), 400
        try:
            stock = int(payload.get("stock_count", template.iloc[0]["stock_count"]))
            restocked = int(payload.get("restocked", 0))
        except (TypeError, ValueError):
            return jsonify({"error": "stock_count and restocked must be integers"}), 400
        if stock < 0 or restocked < 0:
            return jsonify({"error": "counts cannot be negative"}), 400

        row = one_prediction_row(template.iloc[0], item, slot, stock, restocked)
        prediction = float(_load_model(model).predict(row)[0])
        return jsonify({
            "model": model, "item_code": item, "slot": slot,
            "stock_count": stock, "restocked": restocked,
            "predicted_remaining": round(max(0.0, prediction), 2),
            "low_stock": bool(prediction < metrics["low_stock_threshold"]),
            "threshold": metrics["low_stock_threshold"],
        })

    @app.route("/api/log")
    def api_log():
        limit = min(int(request.args.get("limit", 12)), 100)
        rows = (features.sort_values(["date", "item_code", "slot_index"])
                .tail(limit)[["date", "item_code", "slot", "stock_count", "restocked"]])
        return jsonify(rows.to_dict(orient="records"))

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    create_app().run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
