"""Generate the 14-day shelf count log.

IMPORTANT — data provenance
---------------------------
The brief asks for counts logged with a shopkeeper twice per sale period over
14 days. That field visit was not possible for this submission, so this module
produces a *simulation* of such a log. It is deliberately realistic (weekend
lifts, evening peaks, reorder points, finite shelf capacity, integer counts)
but it is NOT a record of any real shop, person or product. Only anonymous
item codes and counts are written — no commercial item-level details.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from .config import (ITEM_PROFILES, N_DAYS, RAW_LOG, ROOT, SALE_PERIODS, SEED,
                     SLOTS, START_DATE, ensure_dirs)


def simulate_log(seed: int = SEED) -> pd.DataFrame:
    """Return a 14-day simulated before/after-sale shelf count log.

    Columns match the brief exactly: date, item_code, slot, stock_count,
    restocked. Rows are ordered chronologically per item.
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range(START_DATE, periods=N_DAYS, freq="D")
    rows: list[dict] = []

    for item, profile in ITEM_PROFILES.items():
        stock = int(profile["opening"])
        for day_idx, date in enumerate(dates):
            restocks_today = 0
            for slot in SLOTS:
                # Sales happen during the two sale periods, never at the
                # "before" checks. Weekends and evenings sell faster.
                if SALE_PERIODS[slot] > 0:
                    weekend_lift = (profile["weekend_lift"]
                                    if date.day_of_week >= 5 else 1.0)
                    drift = 1.0 + 0.012 * day_idx
                    lam = (profile["base_sales"] * SALE_PERIODS[slot]
                           * weekend_lift * drift)
                    demand = max(0, int(rng.poisson(lam) + rng.normal(0, profile["noise"] / 2)))
                    stock = max(0, stock - demand)

                # A delivery/refill is recorded when the shelf is low and
                # there is room for it; rarely twice in one day.
                restocked = 0
                if (stock <= profile["reorder_point"] and restocks_today < 2
                        and rng.random() < 0.88):
                    restocked = int(profile["restock"])
                    stock = min(int(profile["capacity"]), stock + restocked)
                    restocked = stock - max(0, stock - restocked)
                    restocks_today += 1

                rows.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "item_code": item,
                    "slot": slot,
                    "stock_count": int(stock),
                    "restocked": int(restocked),
                })

    return pd.DataFrame(rows, columns=["date", "item_code", "slot",
                                       "stock_count", "restocked"])


def validate_log(df: pd.DataFrame) -> None:
    """Fail loudly if the generated log breaks the brief's schema."""
    assert list(df.columns) == ["date", "item_code", "slot", "stock_count", "restocked"]
    assert len(df) == N_DAYS * len(SLOTS) * len(ITEM_PROFILES)
    assert df["stock_count"].ge(0).all(), "negative stock is impossible"
    assert df["restocked"].ge(0).all(), "restocked is a count of units added"
    assert not df.duplicated(["date", "item_code", "slot"]).any()
    assert df["date"].nunique() == N_DAYS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    df = simulate_log(args.seed)
    validate_log(df)
    ensure_dirs()
    df.to_csv(RAW_LOG, index=False)
    print(f"Wrote {len(df)} simulated log rows to {RAW_LOG.relative_to(ROOT)}")
    print(df.head(8).to_string(index=False))


if __name__ == "__main__":
    main()
