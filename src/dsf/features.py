"""Turn the raw before/after log into a supervised regression table.

Target
------
``remaining_count`` is the stock count at the *next* shelf check for the same
item. Every earlier check is a feature row, so the model learns "given what I
can see now, what will be left when I check again?"

All engineered features use only information available at the current check
(no look-ahead), which keeps the chronological train/test split honest.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import (FEATURE_COLUMNS, MODELLING_SET, RAW_LOG, ROOT, SALE_PERIODS,
                     SLOTS, START_DATE, TARGET, ensure_dirs)

_SLOT_INDEX = {slot: idx for idx, slot in enumerate(SLOTS)}


def build_features(raw: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return the feature table with a (possibly NaN) target column."""
    if raw is None:
        raw = pd.read_csv(RAW_LOG)

    df = raw.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["slot_index"] = df["slot"].map(_SLOT_INDEX).astype(int)
    df["day_index"] = (df["date"] - pd.Timestamp(START_DATE)).dt.days.astype(int)
    df["is_weekend"] = (df["date"].dt.day_of_week >= 5).astype(int)
    df = df.sort_values(["item_code", "date", "slot_index"]).reset_index(drop=True)

    grouped = df.groupby("item_code", sort=False)
    prev_stock = grouped["stock_count"].shift(1)
    # sales = what was on the shelf + what was added - what is on it now
    sales = (prev_stock + df["restocked"] - df["stock_count"]).clip(lower=0)
    df["sales_since_prev"] = sales.fillna(0).astype(int)
    df["prev_sales"] = grouped["sales_since_prev"].shift(1).fillna(0).astype(int)
    df["rolling_sales_3"] = (
        df.groupby("item_code", sort=False)["prev_sales"]
        .transform(lambda s: s.rolling(3, min_periods=1).mean())
        .round(2)
    )

    # How many checks since this item was last topped up (6 = "no history yet").
    since: list[int] = []
    for _, group in df.groupby("item_code", sort=False):
        counter = 6
        for restocked in group["restocked"]:
            counter = 0 if restocked > 0 else counter + 1
            since.append(counter)
    df["checks_since_restock"] = since

    # The check schedule is known in advance: after an "after sale" check the
    # next check is a "before sale" check (no demand), and vice versa.
    next_slot = grouped["slot"].shift(-1)
    df["next_slot"] = next_slot.fillna(SLOTS[0])
    df["next_slot_index"] = df["next_slot"].map(_SLOT_INDEX).astype(int)
    df["next_is_sale"] = df["next_slot"].map(
        lambda s: int(SALE_PERIODS.get(s, 0.0) > 0)).astype(int)
    next_date = grouped["date"].shift(-1).fillna(df["date"] + pd.Timedelta(days=1))
    df["next_weekend"] = (next_date.dt.day_of_week >= 5).astype(int)

    # Causal demand expectation: average units sold in each slot type using
    # ONLY checks already observed for that item (plus a global fallback).
    slot_stats: dict[tuple[str, str], list[float]] = {}
    restock_sizes: dict[str, list[int]] = {}
    reorder_estimate: dict[str, int] = {}
    global_sales = [0.0, 0.0]
    expected: list[float] = []
    expected_restock: list[float] = []
    restock_risk: list[int] = []
    for row in df.itertuples(index=False):
        key = (row.item_code, row.next_slot)
        stats = slot_stats.get(key)
        if stats and stats[1]:
            expected.append(stats[0] / stats[1])
        elif global_sales[1]:
            expected.append(global_sales[0] / global_sales[1])
        else:
            expected.append(3.0)

        risk = int(row.stock_count <= reorder_estimate.get(row.item_code, 0))
        sizes = restock_sizes.get(row.item_code, [])
        restock_risk.append(risk)
        expected_restock.append(round(risk * float(np.median(sizes)) if sizes else 0.0, 2))

        current = (row.item_code, row.slot)
        slot_stats.setdefault(current, [0.0, 0.0])
        slot_stats[current][0] += row.sales_since_prev
        slot_stats[current][1] += 1
        global_sales[0] += row.sales_since_prev
        global_sales[1] += 1
        if row.restocked > 0:
            restock_sizes.setdefault(row.item_code, []).append(row.restocked)
            pre_refill = row.stock_count - row.restocked
            reorder_estimate[row.item_code] = max(
                reorder_estimate.get(row.item_code, 0), pre_refill)

    df["expected_sales_next"] = np.round(expected, 2)
    df["expected_restock_next"] = expected_restock
    df["restock_risk_next"] = restock_risk

    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df[TARGET] = grouped["stock_count"].shift(-1)
    return df[list(dict.fromkeys(
        ["date", "item_code", "slot", "stock_count", "restocked",
         "sales_since_prev"] + list(FEATURE_COLUMNS) + [TARGET]
    ))]


def split_chronologically(df: pd.DataFrame, test_days: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Use the last ``test_days`` of the log as a genuinely unseen test set."""
    train = df[df[TARGET].notna() & (df["day_index"] < df["day_index"].max() - test_days + 1)]
    test = df[df[TARGET].notna() & (df["day_index"] >= df["day_index"].max() - test_days + 1)]
    return train.reset_index(drop=True), test.reset_index(drop=True)


def latest_snapshots(df: pd.DataFrame) -> pd.DataFrame:
    """Most recent feature row for every (item, slot) pair (12 templates)."""
    idx = df.groupby(["item_code", "slot"], sort=True).tail(1).index
    return df.loc[idx].sort_values(["item_code", "slot_index"]).reset_index(drop=True)


def one_prediction_row(template: pd.Series, item_code: str, slot: str,
                       stock_count: int, restocked: int) -> pd.DataFrame:
    """Build a single scoring row from a dashboard form submission."""
    row = template.copy()
    row["item_code"] = item_code
    row["slot"] = slot
    row["slot_index"] = _SLOT_INDEX[slot]
    row["stock_count"] = int(stock_count)
    row["restocked"] = int(restocked)
    return pd.DataFrame([row])[list(FEATURE_COLUMNS)]


def main() -> None:
    ensure_dirs()
    df = build_features()
    df.to_csv(MODELLING_SET, index=False)
    print(f"Wrote {len(df)} feature rows to {MODELLING_SET.relative_to(ROOT)}")
    print(f"Target available for {df[TARGET].notna().sum()} rows; "
          f"{df['item_code'].nunique()} items; "
          f"{df['date'].nunique()} days.")


if __name__ == "__main__":
    main()
