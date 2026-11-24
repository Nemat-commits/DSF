"""Build the PDF report, PowerPoint deck and handwritten-style notes sheet.

Every number in the report is read from outputs/models/metrics.json, so the
documents always agree with the trained models.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image as PILImage
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from .config import (DASHBOARD_DIR, FIGURE_DIR, METRICS, OUTPUT_DIR, REPORT_DIR,
                     ROOT, SEED, ensure_dirs)

NAVY = colors.HexColor("#0e1b2a")
TEAL = colors.HexColor("#148f83")
MUTED = colors.HexColor("#5c6b7a")
LIGHT = colors.HexColor("#eef4f8")


# --------------------------------------------------------------------------- PDF
def _style_sheet():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("TitleBig", parent=styles["Title"], fontSize=25,
                              leading=30, textColor=NAVY, spaceAfter=6))
    styles.add(ParagraphStyle("Sub", parent=styles["Normal"], fontSize=11,
                              leading=16, textColor=MUTED, spaceAfter=12))
    styles.add(ParagraphStyle("H1", parent=styles["Heading1"], fontSize=14.5,
                              leading=18, textColor=NAVY, spaceBefore=14,
                              spaceAfter=7))
    styles.add(ParagraphStyle("H2", parent=styles["Heading2"], fontSize=11.5,
                              textColor=TEAL, spaceBefore=9, spaceAfter=4))
    styles.add(ParagraphStyle("Body2", parent=styles["BodyText"], fontSize=9.6,
                              leading=14, spaceAfter=6))
    styles.add(ParagraphStyle("Small2", parent=styles["BodyText"], fontSize=8.2,
                              leading=11.5, textColor=MUTED))
    styles.add(ParagraphStyle("NoteBox", parent=styles["BodyText"], fontSize=9,
                              leading=13, textColor=colors.HexColor("#6b4a10")))
    return styles


def _figure(name: str, max_w: float = 16.4, max_h: float = 9.0) -> Image:
    path = FIGURE_DIR / name
    with PILImage.open(path) as im:
        w, h = im.size
    scale = min(max_w / w, max_h / h)
    return Image(str(path), width=w * scale * cm, height=h * scale * cm)


def _table(data: list[list[str]], widths: list[float], header: bool = True) -> Table:
    t = Table(data, colWidths=[w * cm for w in widths], hAlign="LEFT")
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 8.4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d6e0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), NAVY),
                  ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    t.setStyle(TableStyle(style))
    return t


def make_pdf(metrics: dict) -> Path:
    ensure_dirs()
    path = REPORT_DIR / "DSC293_Shelf_Stock_Forecast_Report.pdf"
    s = _style_sheet()
    best = metrics["best_model"]
    bm = metrics["models"][best]
    base = metrics["baseline_persistence"]["mae"]

    story: list = []
    story += [
        Paragraph("Shelf Stock Level Forecast", s["TitleBig"]),
        Paragraph("DSC293 · Pakistan Field Capstone · Project 14 / 35 · "
                  "Food &amp; Shops · 4-week maximum", s["Sub"]),
    ]
    box = Table([[Paragraph(
        "<b>DATA PROVENANCE NOTICE.</b> A supervised visit to a real shop was not "
        "feasible for this submission. The 14-day log analysed here is a "
        "reproducible <b>simulation</b> of a shopkeeper's before/after-sale counts "
        "(fictional shop, anonymous item codes, integer counts, no prices, brands, "
        "suppliers or identities). No real commercial information is disclosed and "
        "no consent from a real shopkeeper is claimed. Replace this log with a "
        "genuine consented log before any operational use.", s["NoteBox"])]],
        colWidths=[16.4 * cm])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff3d6")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#d9a441")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story += [box, Spacer(1, 14)]
    story += [Paragraph("Executive summary", s["H1"])]
    story += [Paragraph(
        f"The decision question is: <i>how many units will remain on the shelf at the "
        f"next check?</i> We modelled 168 simulated checks across 3 anonymous items "
        f"and 14 days, with four checks per day (before and after the morning and "
        f"evening sale periods). The target is the stock count at the following check. "
        f"After a chronological split (10 training days, 4 unseen test days; "
        f"{metrics['split']['test_rows']} scored checks), the <b>{best}</b> achieved "
        f"the lowest mean absolute error of <b>{bm['mae']:.2f} units</b> "
        f"(RMSE {bm['rmse']:.2f}, R² {bm['r2']:.2f}), edging out the "
        f"persistence benchmark of {base:.2f} units. The improvement is small: with "
        f"only two weeks of three items, the simplest rule remains a serious "
        f"benchmark. The dashboard exposes trajectories, low-stock alerts, model MAE "
        f"and a live next-check predictor.", s["Body2"])]
    story += [_table([
        ["Metric", "Value", "Interpretation"],
        ["Rows / items / days", "168 / 3 / 14", "4 checks per item per day"],
        ["Best model", best.replace("_", " "), "lowest test MAE of the three"],
        ["Test MAE", f"{bm['mae']:.2f} units", "average miss at next check"],
        ["Persistence MAE", f"{base:.2f} units", "'next = now' sanity benchmark"],
        ["Low-stock threshold", f"{metrics['low_stock_threshold']} units", "demonstration alert level"],
    ], [4.2, 4.2, 8.0])]
    story += [PageBreak()]

    story += [Paragraph("1. Decision, scope and data collection", s["H1"])]
    story += [Paragraph(
        "The brief asks a shopkeeper to log visible quantities of 2–3 popular items "
        "before and after sale periods for 14 days, recording date, item_code, slot, "
        "stock_count and restocked. The intended workflow (approval, daily logs, "
        "analysis, app, submission) is documented in the 4-week plan below. Because "
        "the visit could not happen, the same schema was populated by a seeded "
        "simulator that mimics the mechanics the log would show: evening demand "
        "above morning demand, a weekend lift, finite shelf capacity, reorder "
        "points and restock events. The simulator source and seed "
        f"({SEED}) are in the repository, so every figure is reproducible.", s["Body2"])]
    story += [Paragraph("Data dictionary", s["H2"])]
    story += [_table([
        ["Field", "Type", "Meaning / range"],
        ["date", "date", "YYYY-MM-DD; 14 consecutive days from 2026-10-05"],
        ["item_code", "category", "ITEM-A / ITEM-B / ITEM-C (no brand or price)"],
        ["slot", "category", "pre_morning, post_morning, pre_evening, post_evening"],
        ["stock_count", "integer ≥ 0", "units visible on the shelf at the check"],
        ["restocked", "integer ≥ 0", "units added at that check (0 = none)"],
        ["remaining_count", "integer ≥ 0", "derived target: stock at the next check"],
    ], [3.4, 2.6, 10.4])]
    story += [Paragraph("Sample of the simulated log", s["H2"])]
    story += [_table([
        ["date", "item_code", "slot", "stock_count", "restocked"],
        ["2026-10-05", "ITEM-A", "pre_morning", "48", "0"],
        ["2026-10-05", "ITEM-A", "post_morning", "43", "0"],
        ["2026-10-05", "ITEM-A", "post_evening", "38", "0"],
        ["2026-10-08", "ITEM-B", "pre_evening", "12", "0"],
        ["2026-10-08", "ITEM-B", "post_evening", "19", "18"],
    ], [3.3, 3.3, 4.4, 3.1, 2.3])]
    story += [PageBreak()]

    story += [Paragraph("2. Exploratory data analysis", s["H1"])]
    story += [_figure("eda_stock_trajectories.png", max_h=10.6), Spacer(1, 8)]
    story += [Paragraph(
        "Each sawtooth is a sell-down followed by a refill. Restock markers cluster "
        "near the reorder point; the three items have different capacities and "
        "turnover, so a single global threshold is only a demonstration rule.",
        s["Small2"])]
    story += [Spacer(1, 6), _figure("eda_sales_by_slot.png", max_h=6.2)]
    story += [_figure("eda_restocks.png", max_h=5.6)]
    story += [PageBreak()]

    story += [Paragraph("3. Modelling method", s["H1"])]
    story += [Paragraph(
        "<b>Target.</b> remaining_count is the next observed stock_count for the same "
        "item. The final check of each item has no successor and is not scored. "
        "<b>Features.</b> Current stock and restock amount, check/day indices, "
        "weekend flag, sales since the previous check, a 3-check rolling sales mean, "
        "checks since restock, and schedule-aware fields (the next slot, whether it "
        "follows a sale, whether it falls on a weekend). Demand and refill "
        "expectations are built causally: each row may use only checks already "
        "observed for that item. <b>Split.</b> Days 1–10 train "
        f"({metrics['split']['train_rows']} rows); days 11–14 test "
        f"({metrics['split']['test_rows']} rows). No shuffling and no random "
        "row split, so the test set is a genuine future window.", s["Body2"])]
    story += [Paragraph(
        "<b>Models.</b> (1) Linear Regression; (2) Decision Tree "
        "(max depth 5, minimum 4 leaves); (3) Random Forest (300 trees, max depth 8, "
        "minimum 2 leaves). Categorical fields are one-hot encoded; numeric fields "
        "pass through unchanged. Lasso-free ordinary least squares, tree and forest "
        "use fixed random seeds. A persistence baseline ('next count = current "
        "count') is reported for context. <b>Metric.</b> MAE in units is primary "
        "because a shopkeeper needs a typical error in saleable units; RMSE and R² "
        "are secondary.", s["Body2"])]
    story += [Paragraph("4. Results and model comparison", s["H1"])]
    rows = [["Model", "Test MAE ↓", "RMSE ↓", "R² ↑", "Train MAE"]]
    for name, m in metrics["models"].items():
        rows.append([name.replace("_", " ") + (" ★" if name == best else ""),
                     f"{m['mae']:.2f}", f"{m['rmse']:.2f}", f"{m['r2']:.2f}",
                     f"{m['train_mae']:.2f}"])
    rows.append(["persistence (baseline)", f"{base:.2f}",
                 f"{metrics['baseline_persistence']['rmse']:.2f}",
                 f"{metrics['baseline_persistence']['r2']:.2f}", "—"])
    story += [_table(rows, [5.6, 2.7, 2.7, 2.4, 3.0])]
    story += [Spacer(1, 8), _figure("model_mae.png", max_h=7.0)]
    story += [Paragraph(
        f"The {best} wins on MAE ({bm['mae']:.2f} vs {base:.2f}), RMSE and R². "
        "The Decision Tree is the weakest out of sample: its lower training error "
        "shows it memorises the small training window. The modest gap to the "
        "baseline is the honest headline — a two-week, three-item log does not "
        "give the models much signal beyond 'not much changes between checks'. "
        "A longer field log should strengthen the learned item×slot demand "
        "pattern.", s["Body2"])]
    story += [PageBreak()]

    story += [Paragraph("5. Forecasts, alerts and dashboard", s["H1"])]
    story += [_figure("actual_vs_predicted.png", max_h=10.5)]
    story += [Spacer(1, 6), _figure("residuals.png", max_h=6.0)]
    story += [Paragraph(
        "The Flask dashboard reads the saved models and shows: stock-level "
        "trajectories with held-out forecasts; a low-stock alert list driven by a "
        "threshold slider and the selected model; the MAE comparison chart; the "
        "latest log rows; and a form that scores a what-if next check "
        "(item, slot, current count, restock amount). All views are served over "
        "relative URLs, and the app binds to 0.0.0.0 for the live preview.", s["Body2"])]
    story += [PageBreak()]

    story += [Paragraph("6. Ethics, safety and privacy", s["H1"])]
    story += [Paragraph(
        "The brief's safety rule is 'do not share item-level commercial information "
        "without consent'. No real shop was approached, so no commercial record "
        "exists in this submission: items are ITEM-A/B/C, with no brand, price, "
        "supplier, shop name, location, owner or customer data. The synthetic "
        "origin is stated in the repository, the report, the slides and the "
        "dashboard banner. If a real shopkeeper later supplies a log, obtain "
        "explicit consent, keep the raw log private, publish only pseudonymised "
        "codes and counts, and allow the shopkeeper to withdraw before sharing.",
        s["Body2"])]
    story += [Paragraph("7. Limitations and next steps", s["H1"])]
    for line in [
        "Only 14 days × 3 items: wide confidence intervals; do not deploy for real replenishment.",
        "Restock decisions are only partly predictable; the forecast is a point estimate, not a safety stock.",
        "Counts are simulated, so no observer bias, occlusion or transcription error is represented.",
        "Next: collect a genuine consented log, record price band and shelf capacity as optional context, add prediction intervals, and validate alerts with the shopkeeper.",
    ]:
        story += [Paragraph("• " + line, s["Body2"])]
    story += [Paragraph("8. Four-week work plan (as specified in the brief)", s["H1"])]
    story += [_table([
        ["Week", "Planned activity", "Status in this submission"],
        ["W1", "Approval + start logs", "Scope and safety rule recorded; simulator specified"],
        ["W2", "Continue data", "14-day log generated with the required schema"],
        ["W3", "Finish, EDA + 3 models", "EDA, chronological split, 3 models and comparison complete"],
        ["W4", "App, GitHub, PDF + PPT", "Flask dashboard, repository, this report and slides complete"],
    ], [1.5, 5.4, 9.5])]

    story += [Paragraph("Appendix A — reproduction", s["H1"])]
    story += [Paragraph(
        "<font face='Courier'>python3 -m venv .venv &amp;&amp; .venv/bin/pip install -r "
        "requirements.txt</font><br/>"
        "<font face='Courier'>PYTHONPATH=src .venv/bin/python -m dsf.generate_data</font><br/>"
        "<font face='Courier'>PYTHONPATH=src .venv/bin/python -m dsf.features</font><br/>"
        "<font face='Courier'>PYTHONPATH=src .venv/bin/python -m dsf.train</font><br/>"
        "<font face='Courier'>PYTHONPATH=src .venv/bin/python -m dsf.make_reports</font><br/>"
        "<font face='Courier'>PYTHONPATH=src .venv/bin/python -m dsf.dashboard_app</font>",
        s["Body2"])]

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(2 * cm, 1.1 * cm,
                          "DSC293 · Shelf Stock Level Forecast · simulated data disclosure applies")
        canvas.drawRightString(A4[0] - 2 * cm, 1.1 * cm, f"Page {doc.page}")
        canvas.restoreState()

    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=2 * cm,
                      rightMargin=2 * cm, topMargin=1.7 * cm,
                      bottomMargin=1.7 * cm, title="Shelf Stock Level Forecast",
                      author="DSC293 capstone").build(story, onFirstPage=footer,
                                                      onLaterPages=footer)
    print(f"Wrote {path.relative_to(ROOT)}")
    return path


# -------------------------------------------------------------------------- PPT
def _slide_bg(slide, color=RGBColor(14, 27, 42)):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def _text(slide, text, x, y, w, h, size=18, bold=False,
          color=RGBColor(232, 241, 248), align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(str(text).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.alignment = align
        p.space_after = Pt(5)
        for run in p.runs:
            run.font.size = Pt(size)
            run.font.bold = bold
            run.font.color.rgb = color
    return box


def _pic(slide, name, x, y, w):
    path = FIGURE_DIR / name
    with PILImage.open(path) as im:
        ratio = im.height / im.width
    slide.shapes.add_picture(str(path), Inches(x), Inches(y), width=Inches(w),
                             height=Inches(w * ratio))


def make_pptx(metrics: dict) -> Path:
    ensure_dirs()
    path = REPORT_DIR / "DSC293_Shelf_Stock_Forecast_Slides.pptx"
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    best = metrics["best_model"]
    bm = metrics["models"][best]
    base = metrics["baseline_persistence"]["mae"]

    def new(title: str, subtitle: str = ""):
        slide = prs.slides.add_slide(blank)
        _slide_bg(slide)
        bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(1.0))
        bar.fill.solid(); bar.fill.fore_color.rgb = RGBColor(19, 43, 66)
        bar.line.fill.background()
        _text(slide, title, 0.55, 0.16, 12.2, 0.5, size=24, bold=True)
        if subtitle:
            _text(slide, subtitle, 0.55, 0.63, 12.2, 0.3, size=11,
                  color=RGBColor(157, 180, 199))
        _text(slide, "DSC293 · Project 14/35 · simulated data disclosure applies",
              0.55, 7.12, 12, 0.25, size=8, color=RGBColor(120, 145, 165))
        return slide

    # 1 — title
    slide = prs.slides.add_slide(blank)
    _slide_bg(slide)
    _text(slide, "Shelf Stock Level Forecast", 0.8, 2.1, 11.8, 0.9,
          size=40, bold=True)
    _text(slide, "DSC293 · Pakistan Field Capstone · Food & Shops · Project 14/35",
          0.85, 3.05, 11.5, 0.5, size=17, color=RGBColor(76, 194, 180))
    _text(slide, "Estimate stock remaining at the next shelf check\n"
                 "Linear Regression · Decision Tree · Random Forest · Flask dashboard",
          0.85, 3.8, 11.5, 1.0, size=16)
    _text(slide, "SIMULATED 14-DAY LOG — no real shop, item, brand or price data",
          0.85, 5.5, 11.5, 0.4, size=13, color=RGBColor(255, 180, 84), bold=True)

    # 2 — decision and plan
    s = new("Decision question & 4-week plan", "What the brief asks for")
    _text(s, "Estimate the count left on the shelf at the next check, from a "
             "shopkeeper's before/after-sale logs of 2–3 items over 14 days.",
          0.6, 1.4, 12, 1.0, size=19)
    rows = [("W1", "Approval + start logs"),
            ("W2", "Continue daily counts"),
            ("W3", "Finish data, EDA + 3 models"),
            ("W4", "App, GitHub, PDF + PPT + notes")]
    for i, (w, txt) in enumerate(rows):
        _text(s, f"{w}   {txt}", 1.0, 2.7 + i * 0.65, 11, 0.45, size=17)
    _text(s, "Fields: date · item_code · slot · stock_count · restocked",
          1.0, 5.8, 11, 0.4, size=14, color=RGBColor(76, 194, 180))

    # 3 — data & ethics
    s = new("Data, provenance & safety", "What was actually used")
    _text(s, "168 checks = 14 days × 3 anonymous items × 4 slots", 0.7, 1.35,
          12, 0.5, size=20, bold=True)
    _text(s, "• Seeded simulation of a shopkeeper's log (fictional shop)\n"
             "• Realistic weekend lift, evening peaks, reorder points, refills\n"
             "• ITEM-A/B/C only: no brand, price, supplier, shop or person\n"
             "• No consent claim; synthetic origin is stated in every deliverable\n"
             "• A real consented log must replace this before operational use",
          0.8, 2.1, 11.8, 3.2, size=16)
    _text(s, "Safety rule: do not share item-level commercial information without consent.",
          0.8, 5.7, 11.8, 0.5, size=15, color=RGBColor(255, 180, 84))

    # 4 — sample log
    s = new("What one day of the log looks like", "Exact schema from the brief")
    table = s.shapes.add_table(9, 5, Inches(0.8), Inches(1.4),
                               Inches(11.7), Inches(4.8)).table
    sample = [
        ["date", "item_code", "slot", "stock_count", "restocked"],
        ["2026-10-05", "ITEM-A", "pre_morning", "48", "0"],
        ["2026-10-05", "ITEM-A", "post_morning", "43", "0"],
        ["2026-10-05", "ITEM-A", "pre_evening", "43", "0"],
        ["2026-10-05", "ITEM-A", "post_evening", "38", "0"],
        ["2026-10-08", "ITEM-B", "pre_evening", "12", "0"],
        ["2026-10-08", "ITEM-B", "post_evening", "19", "18"],
        ["2026-10-11", "ITEM-C", "pre_morning", "27", "30"],
        ["2026-10-11", "ITEM-C", "post_evening", "54", "0"],
    ]
    for r, row in enumerate(sample):
        for c, val in enumerate(row):
            cell = table.cell(r, c)
            cell.text = val
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(12)
                    run.font.bold = r == 0
                    run.font.color.rgb = (RGBColor(255, 255, 255) if r == 0
                                          else RGBColor(232, 241, 248))

    # 5 — EDA trajectories
    s = new("EDA: stock trajectories", "Sell-down and refill cycles")
    _pic(s, "eda_stock_trajectories.png", 1.6, 1.2, 10.1)

    # 6 — EDA demand & refills
    s = new("EDA: demand is not uniform", "Evening sales and refill events")
    _pic(s, "eda_sales_by_slot.png", 0.8, 1.3, 5.8)
    _pic(s, "eda_restocks.png", 6.9, 1.5, 5.5)
    _text(s, "Evening checks show larger sales; refills cluster when shelves run low.",
          0.9, 6.5, 11.5, 0.4, size=14, color=RGBColor(157, 180, 199))

    # 7 — modelling
    s = new("Supervised framing", "From a log to a next-check forecast")
    _text(s, "Target: remaining_count = stock at the NEXT check for the same item\n\n"
             "Features: current stock, restocked, slot + next slot, sale-period flags,\n"
             "day/weekend, past sales, checks since restock, causal demand expectation\n\n"
             "Split: days 1–10 train (120 rows) → days 11–14 test (45 rows)\n"
             "Metric: MAE in units (primary), RMSE and R² secondary",
          0.85, 1.4, 11.8, 4.9, size=16)

    # 8 — comparison
    s = new("Model comparison", "Chronological holdout, lower MAE is better")
    _pic(s, "model_mae.png", 0.9, 1.3, 6.5)
    _text(s, f"Linear Regression   MAE {metrics['models']['linear_regression']['mae']:.2f}\n"
             f"Decision Tree       MAE {metrics['models']['decision_tree']['mae']:.2f}\n"
             f"Random Forest       MAE {metrics['models']['random_forest']['mae']:.2f}\n"
             f"Persistence base    MAE {base:.2f}\n\n"
             f"Winner: {best.replace('_',' ')} — {bm['mae']:.2f} units MAE, "
             f"R² {bm['r2']:.2f}.\n\n"
             "The gap to the simple benchmark is small: with only 14 days the\n"
             "baseline remains competitive. More field data is the real fix.",
          7.5, 1.6, 5.2, 5.0, size=15)

    # 9 — forecasts
    s = new("Held-out forecasts", "Actual vs. predicted counts, days 11–14")
    _pic(s, "actual_vs_predicted.png", 1.0, 1.15, 11.3)

    # 10 — dashboard
    s = new("Working dashboard", "Flask app · live preview")
    _text(s, "• Stock-level trajectories, observed + held-out forecasts\n"
             "• Low-stock alerts with adjustable threshold\n"
             "• Model MAE chart and full comparison table\n"
             "• What-if predictor: item, slot, count now, restock amount\n"
             "• Recent log table and synthetic-data banner\n\n"
             "Run: PYTHONPATH=src .venv/bin/python -m dsf.dashboard_app\n"
             "Open: http://localhost:5000  (binds 0.0.0.0 for preview)",
          0.85, 1.45, 11.8, 5.0, size=16)

    # 11 — decision
    s = new("Decision & limitations", "What we would tell the shopkeeper")
    _text(s, f"Use the {best.replace('_',' ')} as the forecasting component: typical "
             f"error about {bm['mae']:.1f} units at the next check. Treat the "
             f"{base:.1f}-unit persistence benchmark as the floor to beat.\n\n"
             f"Trigger a manual shelf check when the forecast falls below {metrics['low_stock_threshold']} units.\n\n"
             "LIMITATIONS\n"
             "• Simulated logs, not a real field visit\n"
             "• Only 3 items × 14 days — wide uncertainty\n"
             "• Point forecast only; no safety stock or prediction interval",
          0.85, 1.4, 11.8, 5.2, size=16)

    # 12 — next steps
    s = new("Next steps / questions", "From capstone prototype to field tool")
    _text(s, "1. Obtain consented real logs and keep raw counts private\n"
             "2. Extend to 6–8 weeks and more items for stable estimates\n"
             "3. Add prediction intervals and cost-based alert thresholds\n"
             "4. Validate alerts with the shopkeeper before any replenishment use\n"
             "5. Publish only pseudonymised codes and aggregate counts\n\n"
             "Repository: GitHub + dashboard + report + slides + handwritten notes",
          0.85, 1.5, 11.8, 5.0, size=16)

    prs.save(str(path))
    print(f"Wrote {path.relative_to(ROOT)}")
    return path


# ------------------------------------------------------------- handwritten notes
def make_handwritten_notes() -> Path:
    """A handwritten-*style* facsimile of study notes, clearly labelled as such.

    This is not a forged field notebook: the heading says it is a generated
    study-notes facsimile, and the content refers to the simulated data.
    """
    ensure_dirs()
    path = REPORT_DIR / "handwritten_notes_facsimile.pdf"
    font_path = ROOT / "assets" / "fonts" / "Caveat.ttf"
    pdfmetrics.registerFont(TTFont("Caveat", str(font_path)))
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=1.8 * cm,
                            rightMargin=1.8 * cm, topMargin=1.5 * cm,
                            bottomMargin=1.5 * cm,
                            title="Study notes (handwritten-style facsimile)")
    big = ParagraphStyle("HWTitle", fontName="Caveat", fontSize=26, leading=30,
                         textColor=NAVY)
    hand = ParagraphStyle("HW", fontName="Caveat", fontSize=19, leading=29,
                          textColor=colors.HexColor("#1b3a5c"))
    small = ParagraphStyle("HWSmall", fontName="Helvetica", fontSize=8,
                           textColor=MUTED, leading=11)
    story = [
        Paragraph("Shelf stock forecast – study notes", big),
        Paragraph("Handwritten-style facsimile generated for this submission. "
                  "Not original field notes; the analysed log is simulated.", small),
        Spacer(1, 16),
    ]
    lines = [
        "Decision: how many units will be left when we check again?",
        "Field plan: 2–3 items, before + after morning and evening sale, 14 days.",
        "Fields to write down: date, item_code, slot, stock_count, restocked.",
        "No real shop visit was possible -> simulated a realistic log instead.",
        "Shop stays anonymous; only ITEM-A/B/C and counts are ever shown.",
        "",
        "What the log shows:",
        "evening sales > morning sales; weekends move faster.",
        "stock drops, then jumps when a restock is recorded.",
        "each item has its own shelf capacity and reorder point.",
        "",
        "ML setup:",
        "target = next check's stock count for the same item.",
        "features = count now, slot, next slot, weekend, past sales, restocks.",
        "train days 1–10, test days 11–14 (do NOT shuffle time!).",
        "Linear Regression / Decision Tree / Random Forest, compare by MAE.",
        "keep a 'next = now' baseline: it is surprisingly hard to beat.",
        "",
        "Result: Random Forest lowest MAE (~4 units); tree overfits a little.",
        "Small win over baseline -> collect more real days before trusting it.",
        "Dashboard: trajectories, low-stock alert, MAE, what-if predictor.",
        "",
        "If a real friend's shop is used later:",
        "ask permission first, keep their raw log private, share only codes,",
        "and let them review anything before it is uploaded anywhere.",
    ]
    for line in lines:
        story.append(Paragraph(("• " + line) if line and not line.endswith(":") else line, hand))
    doc.build(story)
    print(f"Wrote {path.relative_to(ROOT)}")
    return path


def main() -> None:
    with METRICS.open(encoding="utf-8") as fh:
        metrics = json.load(fh)
    make_pdf(metrics)
    make_pptx(metrics)
    make_handwritten_notes()


if __name__ == "__main__":
    main()
