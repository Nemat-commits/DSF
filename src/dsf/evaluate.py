"""Charts for the EDA and the model comparison."""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import (FIGURE_DIR, ITEM_PROFILES, LOW_STOCK_THRESHOLD, TARGET,
                     ensure_dirs)

COLORS = {"ITEM-A": "#e8833a", "ITEM-B": "#3a86b7", "ITEM-C": "#4f9d69"}


def _save(fig: plt.Figure, name: str) -> None:
    ensure_dirs()
    path = FIGURE_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  figure: {path.relative_to(FIGURE_DIR.parent.parent)}")


def plot_eda(df: pd.DataFrame) -> None:
    """Stock trajectories, sales by slot and restock frequency."""
    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
    for ax, (item, profile) in zip(axes, ITEM_PROFILES.items()):
        part = df[df["item_code"] == item]
        ax.plot(part["date"], part["stock_count"], color=COLORS[item],
                marker="o", markersize=3, linewidth=1.6, label="count at check")
        refills = part[part["restocked"] > 0]
        ax.scatter(refills["date"], refills["stock_count"], marker="^", s=55,
                   color="#1b6b3a", zorder=5, label="restock recorded")
        ax.axhline(profile["reorder_point"], linestyle="--", linewidth=1,
                   color="#c0392b", alpha=0.8, label="reorder point")
        ax.set_ylabel("units on shelf")
        ax.set_title(f"{item} — 14-day stock trajectory (simulated log)")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8, loc="upper left")
    axes[-1].tick_params(axis="x", rotation=45)
    fig.suptitle("Shelf stock trajectories and restock events", fontsize=14,
                 fontweight="bold")
    fig.tight_layout()
    _save(fig, "eda_stock_trajectories.png")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    sale_rows = df[df["sales_since_prev"] > 0]
    ax.boxplot([sale_rows.loc[sale_rows["slot"] == slot, "sales_since_prev"]
                for slot in ("post_morning", "post_evening")],
               tick_labels=["after morning sale", "after evening sale"])
    ax.set_ylabel("units sold between checks")
    ax.set_title("Demand is higher in the evening sale period")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    _save(fig, "eda_sales_by_slot.png")

    fig, ax = plt.subplots(figsize=(8, 4))
    counts = df[df["restocked"] > 0].groupby("item_code")["restocked"].agg(
        ["count", "sum"])
    counts = counts.reindex(list(ITEM_PROFILES))
    ax.bar(counts.index, counts["count"], color=[COLORS[i] for i in counts.index])
    for i, (n, total) in enumerate(zip(counts["count"], counts["sum"])):
        ax.text(i, n + 0.2, f"{n} refills\n{int(total)} units", ha="center", fontsize=9)
    ax.set_ylim(0, max(counts["count"]) + 3)
    ax.set_ylabel("number of restock events")
    ax.set_title("Restock events recorded during the 14 days")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    _save(fig, "eda_restocks.png")


def plot_results(df: pd.DataFrame, predictions: pd.DataFrame,
                 metrics: dict) -> None:
    """Model MAE, forecasts against actual counts and residual distribution."""
    names = list(metrics["models"])
    maes = [metrics["models"][n]["mae"] for n in names]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    bars = ax.bar(names, maes, color=["#3a86b7", "#e8833a", "#4f9d69"][:len(names)])
    baseline = metrics["baseline_persistence"]["mae"]
    ax.axhline(baseline, color="#7f8c8d", linestyle="--", linewidth=1.5,
               label=f"persistence baseline MAE = {baseline:.2f}")
    for bar, value in zip(bars, maes):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.05,
                f"{value:.2f}", ha="center", fontweight="bold")
    ax.set_ylabel("MAE on held-out days (units)")
    ax.set_title("Model comparison — lower is better")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    _save(fig, "model_mae.png")

    best = metrics["best_model"]
    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    for ax, (item, _) in zip(axes, ITEM_PROFILES.items()):
        part = predictions[predictions["item_code"] == item]
        x = range(len(part))
        ax.plot(x, part["actual"], color="#222222", marker="o", markersize=3,
                label="actual next count")
        ax.plot(x, part[best], color=COLORS[item], marker="x", markersize=4,
                label=f"{best} forecast")
        ax.axhline(LOW_STOCK_THRESHOLD, color="#c0392b", linestyle=":",
                   linewidth=1, label="low-stock threshold")
        ax.set_ylabel("units")
        ax.set_title(item)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    axes[-1].set_xticks(list(range(len(predictions))))
    axes[-1].set_xticklabels(predictions["date"], rotation=60, fontsize=7)
    fig.suptitle("Held-out days: actual vs. forecast shelf counts", fontweight="bold")
    fig.tight_layout()
    _save(fig, "actual_vs_predicted.png")

    residuals = predictions[best] - predictions["actual"]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(residuals, bins=20, color="#3a86b7", edgecolor="white")
    ax.axvline(0, color="#c0392b", linestyle="--")
    ax.set_xlabel("forecast error (predicted - actual) units")
    ax.set_ylabel("checks")
    ax.set_title(f"Residual distribution — {best}")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    _save(fig, "residuals.png")
