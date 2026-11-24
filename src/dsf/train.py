"""Train and compare Linear Regression, Decision Tree and Random Forest.

The split is chronological: the first 10 days train, the final 4 days test.
MAE (mean absolute error in units left on the shelf) is the headline metric
because the decision question is an estimate of remaining stock, not a
classification. A persistence baseline ("tomorrow = today") is reported so the
tree models' value can be judged fairly.
"""

from __future__ import annotations

import argparse
import json
import shutil

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeRegressor

from .config import (CATEGORICAL_FEATURES, FEATURE_COLUMNS, LOW_STOCK_THRESHOLD,
                     METRICS, MODEL_DIR, NUMERIC_FEATURES, PREDICTIONS,
                     PROCESSED_DIR, SEED, TARGET, TEST_DAYS, ensure_dirs)
from .evaluate import plot_eda, plot_results
from .features import build_features, split_chronologically


def make_pipelines(seed: int) -> dict:
    """Return the three named scikit-learn pipelines required by the brief."""
    preprocess = ColumnTransformer([
        ("categorical", OneHotEncoder(handle_unknown="ignore"),
         list(CATEGORICAL_FEATURES)),
        ("numeric", "passthrough", list(NUMERIC_FEATURES)),
    ])
    estimators = {
        "linear_regression": LinearRegression(),
        "decision_tree": DecisionTreeRegressor(max_depth=5, min_samples_leaf=4,
                                               random_state=seed),
        "random_forest": RandomForestRegressor(n_estimators=300, max_depth=8,
                                               min_samples_leaf=2,
                                               random_state=seed, n_jobs=-1),
    }
    return {name: Pipeline([("prep", preprocess), ("model", est)])
            for name, est in estimators.items()}


def score(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    """Metric bundle; MAE is the decision metric."""
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 3),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 3),
        "r2": round(float(r2_score(y_true, y_pred)), 3),
    }


def train_and_evaluate(seed: int = SEED, test_days: int = TEST_DAYS) -> dict:
    """Run the full experiment and write models, metrics, charts and tables."""
    ensure_dirs()
    df = build_features()
    train, test = split_chronologically(df, test_days)
    x_train, y_train = train[list(FEATURE_COLUMNS)], train[TARGET]
    x_test, y_test = test[list(FEATURE_COLUMNS)], test[TARGET]

    plot_eda(df)

    results: dict[str, dict] = {}
    predictions = test[["date", "item_code", "slot", "stock_count", TARGET]].copy()
    predictions = predictions.rename(columns={TARGET: "actual"})

    for name, pipeline in make_pipelines(seed).items():
        pipeline.fit(x_train, y_train)
        pred = pipeline.predict(x_test)
        predictions[name] = np.round(pred, 2)
        results[name] = score(y_test, pred)
        results[name]["train_mae"] = round(float(
            mean_absolute_error(y_train, pipeline.predict(x_train))), 3)
        joblib.dump(pipeline, MODEL_DIR / f"{name}.joblib")
        print(f"  model: {name:18s} test MAE = {results[name]['mae']:.3f} units")

    baseline_pred = test["stock_count"].to_numpy()
    baseline = score(y_test, baseline_pred)
    best = min(results, key=lambda k: results[k]["mae"])
    shutil.copyfile(MODEL_DIR / f"{best}.joblib", MODEL_DIR / "best_model.joblib")

    metrics = {
        "seed": seed,
        "target": TARGET,
        "primary_metric": "MAE (units remaining at next check)",
        "split": {
            "train_rows": int(len(train)),
            "test_rows": int(len(test)),
            "train_days": f"{train['date'].min()} to {train['date'].max()}",
            "test_days": f"{test['date'].min()} to {test['date'].max()}",
            "method": "chronological holdout (no shuffling)",
        },
        "models": results,
        "baseline_persistence": baseline,
        "best_model": best,
        "low_stock_threshold": int(LOW_STOCK_THRESHOLD),
    }
    with METRICS.open("w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)

    predictions.to_csv(PREDICTIONS, index=False)
    df.to_csv(PROCESSED_DIR / "features_full.csv", index=False)
    plot_results(df, predictions, metrics)

    print(f"\nBest model: {best} (MAE {results[best]['mae']:.2f} units; "
          f"persistence baseline {baseline['mae']:.2f})")
    print(f"Metrics: {METRICS.relative_to(METRICS.parents[1])}")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--test-days", type=int, default=TEST_DAYS)
    args = parser.parse_args()
    train_and_evaluate(args.seed, args.test_days)


if __name__ == "__main__":
    main()
