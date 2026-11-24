"""Central configuration for the shelf stock forecasting project.

All paths are resolved from the repository root so the scripts work from any
working directory. The random seed makes the simulated field log reproducible.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = ROOT / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"
MODEL_DIR = OUTPUT_DIR / "models"
REPORT_DIR = OUTPUT_DIR / "reports"
DASHBOARD_DIR = ROOT / "dashboard"

RAW_LOG = RAW_DIR / "shop_log_14days.csv"
MODELLING_SET = PROCESSED_DIR / "modelling_dataset.csv"
PREDICTIONS = PROCESSED_DIR / "test_predictions.csv"
METRICS = MODEL_DIR / "metrics.json"

SEED = 20261124
START_DATE = "2026-10-05"
N_DAYS = 14
TEST_DAYS = 4
LOW_STOCK_THRESHOLD = 20

SLOTS = ("pre_morning", "post_morning", "pre_evening", "post_evening")
SALE_PERIODS = {"pre_morning": 0.0, "post_morning": 0.85,
                "pre_evening": 0.0, "post_evening": 1.25}

# Only anonymous codes and aggregate counts are stored: no brand, price,
# supplier or shopkeeper identity is recorded (see safety note in README).
ITEM_PROFILES = {
    "ITEM-A": {"opening": 48, "base_sales": 5.0, "restock": 24,
               "reorder_point": 14, "capacity": 72, "weekend_lift": 1.35,
               "noise": 1.6},
    "ITEM-B": {"opening": 30, "base_sales": 3.0, "restock": 18,
               "reorder_point": 9, "capacity": 54, "weekend_lift": 1.15,
               "noise": 1.1},
    "ITEM-C": {"opening": 60, "base_sales": 7.0, "restock": 30,
               "reorder_point": 18, "capacity": 90, "weekend_lift": 1.50,
               "noise": 2.0},
}

NUMERIC_FEATURES = (
    "stock_count", "restocked", "day_index", "slot_index", "is_weekend",
    "prev_sales", "rolling_sales_3", "checks_since_restock",
    "next_slot_index", "next_is_sale", "next_weekend", "expected_sales_next",
    "expected_restock_next", "restock_risk_next",
)
CATEGORICAL_FEATURES = ("item_code", "slot", "next_slot")
FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES
TARGET = "remaining_count"


def ensure_dirs() -> None:
    """Create every output directory used by the pipeline."""
    for folder in (RAW_DIR, PROCESSED_DIR, FIGURE_DIR, MODEL_DIR, REPORT_DIR,
                   DASHBOARD_DIR):
        folder.mkdir(parents=True, exist_ok=True)
