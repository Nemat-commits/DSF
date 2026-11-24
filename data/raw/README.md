# Simulated 14-day shelf log — data dictionary

Source: `src/dsf/generate_data.py` (seed `20261124`). This file is a **simulation**
set in a fictional Abbottabad neighbourhood shop. It is **not** a record of a real
shop, and no shopkeeper in Abbottabad supplied data. See the top-level README for
the full disclosure and `docs/DATA_COLLECTION_PROTOCOL.md` for how to gather a
genuine consented log.

| Field | Type | Description |
|---|---|---|
| `date` | date (`YYYY-MM-DD`) | 14 consecutive days starting 2026-10-05 |
| `item_code` | category | `ITEM-A`, `ITEM-B`, `ITEM-C` — anonymous, no brand/price |
| `slot` | category | `pre_morning`, `post_morning`, `pre_evening`, `post_evening` |
| `stock_count` | integer ≥ 0 | units visible on the shelf at the check (after any restock) |
| `restocked` | integer ≥ 0 | units added at that check; 0 means none |

Derived modelling target (in `data/processed/modelling_dataset.csv`):
`remaining_count` = `stock_count` at the next check for the same item.

No shop name, location, owner, customer, supplier, brand or price is recorded.
