# DSC293 — Shelf Stock Level Forecast

**Project 14/35 · Food & Shops · 4-week capstone**

Decision question: *estimate how many units will remain on the shelf at the next check.*
The submission contains a 14-day before/after-sale log, EDA, three regression models
with a chronological comparison, a working Flask dashboard, a PDF report, a PPT deck
and a handwritten-style notes sheet.

> ## Data provenance — read this first
> A real shop visit was not feasible, so the log is a **reproducible simulation** of
> a shopkeeper's log, set in a **fictional Abbottabad neighbourhood shop** (anonymous
> `ITEM-A/B/C`, four checks per day for 14 days). It is realistic in structure and
> behaviour — weekend lift, evening peaks, reorder points, restocks — but it is
> **not** a record of any real shop, person, brand, price or supplier. No shopkeeper
> in Abbottabad was visited or supplied data, and no evidence photos are claimed. No
> item-level commercial information is disclosed. If a real shop later provides a
> log, obtain explicit consent, keep the raw log private and publish only
> pseudonymised codes and counts. `docs/DATA_COLLECTION_PROTOCOL.md` and
> `outputs/reports/field_log_blank_template.pdf` are the kit for doing that.

## Results (chronological holdout: train days 1–10, test days 11–14)

| Model | Test MAE ↓ | RMSE ↓ | R² ↑ |
|---|---:|---:|---:|
| Linear Regression | 4.61 | 6.12 | 0.639 |
| Decision Tree | 4.55 | 6.12 | 0.639 |
| **Random Forest (best)** | **4.02** | **5.82** | **0.673** |
| Persistence baseline ("next = now") | 4.07 | 6.56 | 0.585 |

The forest wins on every metric, but only narrowly on MAE: a two-week, three-item
log does not give much signal beyond persistence. That is reported honestly in the
PDF and slides; more consented field days are the real remedy. The dashboard's
demonstration low-stock threshold is 20 units (adjustable in the UI).

## Quickstart

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

PYTHONPATH=src .venv/bin/python -m dsf.generate_data   # 168-row simulated log
PYTHONPATH=src .venv/bin/python -m dsf.features        # next-check target + features
PYTHONPATH=src .venv/bin/python -m dsf.train           # 3 models, metrics, figures
PYTHONPATH=src .venv/bin/python -m dsf.make_reports    # PDF, PPTX, notes
PYTHONPATH=src .venv/bin/python -m dsf.dashboard_app   # dashboard on :5000
```

Or run everything except the server with `bash run_all.sh`.
Tests: `.venv/bin/python -m pytest -q` (the test configuration adds `src` to the path).

## Repository map

```
data/raw/shop_log_14days.csv          # exact brief schema: date, item_code, slot, stock_count, restocked
data/raw/README.md                    # data dictionary + provenance
data/processed/                       # feature table and held-out predictions
src/dsf/                              # simulator, features, training, evaluation, dashboard, reports
outputs/figures/                      # EDA and model charts
outputs/models/                       # three joblib pipelines + metrics.json
outputs/reports/                      # PDF report, PPTX slides, notes, blank field log
docs/DATA_COLLECTION_PROTOCOL.md      # consent + real 14-day collection protocol
dashboard/templates/index.html        # dashboard UI
tests/                                # schema, pipeline and dashboard smoke tests
assets/fonts/                         # Caveat font (SIL OFL) for the notes facsimile
```

## Dashboard

`http://localhost:5000` (server binds `0.0.0.0` for the Arena live preview) shows:
stock trajectories with held-out forecasts, model-switchable low-stock alerts with a
threshold slider, the MAE comparison, a recent-log table and a form that scores a
what-if next check. All browser calls use relative URLs.

## Deliverables

- `outputs/reports/DSC293_Shelf_Stock_Forecast_Report.pdf` — 6-page report
- `outputs/reports/DSC293_Shelf_Stock_Forecast_Slides.pptx` — 12-slide deck
- `outputs/reports/handwritten_notes_facsimile.pdf` — handwritten-style **study notes
  facsimile** (generated, not forged field notes; labelled as such on the page)
- GitHub repository + this branch, working dashboard, model comparison, dataset

## Git

Work happens on the current branch `arena/c103ef4d-dsf`:

```bash
git status
git add -A && git commit -m "Complete shelf stock forecast capstone"
git push origin arena/c103ef4d-dsf
```

## Google Drive note

The connected Drive has heavy files already organised in folders. Largest items
found: `ScientificCalculatorPro-3.1.0-universal.apk` (52.4 MB) in **Scientific
Calculator Pro**, `terrastep-prototype-v0.1.10-debug.apk` (45.3 MB) and
`terrasteps-milestone30-v0.3.0-arm64-v8a-release.apk` (41.0 MB) in
**TerraSteps - FYP / 04_Builds_&_Defense_Archive**, and two `from-idea-to-app-with-claude-code`
MP4s (32.9 / 32.6 MB) in **From idea to app with Claude Code**. They were left
where they are. A new folder `DSC293_Shelf_Stock_Forecast` holds the uploaded
submission copies of the report, slides, notes, dataset and dashboard screenshot
where available.
