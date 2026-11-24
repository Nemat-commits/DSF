# How to collect the real 14-day log (for a genuine field visit)

This pack is for collecting **actual** data if you or a classmate can visit a
shop with the owner's permission. It does not replace the simulated dataset
currently used by the pipeline. Only swap `data/raw/shop_log_14days.csv` for a
real log once you have consent.

## 1. Ask first — plain-language consent note

> Hello, I am a student working on a course project about how shop shelves run
> out of stock. Would you allow me to write down the **number of units visible**
> on the shelf for two or three everyday items, before and after your morning
> and evening sale periods, for 14 days? I will use only codes like ITEM-A,
> ITEM-B, ITEM-C — no shop name, prices, brands, supplier details, customer
> information or photos of people. You can say no at any point and ask me to
> stop or delete what I recorded.

Get an explicit yes. Write down the date of the conversation and who agreed.
Keep that note private; do not publish names or signatures.

## 2. What to record, exactly

Fields required by the brief (same as the simulated CSV):

| Field | How to fill it |
|---|---|
| `date` | `YYYY-MM-DD`, the calendar date of the check |
| `item_code` | Your own anonymous code: `ITEM-A`, `ITEM-B`, `ITEM-C` |
| `slot` | `pre_morning`, `post_morning`, `pre_evening`, `post_evening` |
| `stock_count` | Units you can actually see on the shelf at that moment |
| `restocked` | Units added at that check; write `0` if none |

Slot meanings: **pre_morning** = just before the morning selling period;
**post_morning** = just after it; **pre_evening** = before the evening rush;
**post_evening** = after closing/settling. Use the same three items every day.

Print `outputs/reports/field_log_blank_template.pdf` or use
`data/raw/field_log_template.csv` (header only) to fill in by hand or in a sheet.

## 3. Photos — only if the shopkeeper says yes

- Ask separately for photo permission; a yes to counts is not a yes to photos.
- Photograph the **shelf area/counting moment**, not faces, receipts, price tags
  or supplier labels. Keep images on your own device.
- If a photo will be submitted or shared, get specific permission for that too,
  and keep it with the consent note. If permission is not given, do not take or
  submit one — a handwritten log is sufficient evidence of collection.
- Never stage a photo to imply a visit that did not happen, and never reuse
  someone else's photo as your own evidence.

## 4. What genuine evidence looks like

- A completed dated log sheet covering all 14 days (or the raw sheet you filled in).
- The shopkeeper's agreement to the counts being used, recorded privately.
- Optional shelf photos, only with the permissions above.
- A short note on any missed checks and why (e.g. shop closed) — real data has gaps.

## 5. Privacy when you hand it in

Publish only the five fields above with anonymous codes. Do not include the
shop's name, address, owner's name, prices, brands or supplier information.
If the shopkeeper later withdraws consent, remove the raw log from your
submission and stop using the derived figures.

## 6. What changes in the project when real data arrives

1. Replace `data/raw/shop_log_14days.csv` with the consented log (same columns).
2. Update `data/raw/README.md` provenance text to describe the real collection.
3. Re-run: `bash run_all.sh` — features, models, figures, PDF and slides rebuild.
4. Tell the dashboard/report that provenance is now real data, and attach the
   consent note and photos according to the permissions you received.
