#!/usr/bin/env python3
"""
visualize.py — generate PNG charts from comparison.json produced by fetch_compare.py

Usage:
    python3 visualize.py <out_dir>

Produces in <out_dir>/charts/:
    01_aum_history.png             — total 13F AUM ($B) across quarters
    02_top15_ribbon.png            — Top-15 latest holdings, value per quarter (grouped bars)
    03_top15_share_trajectory.png  — Top-15 latest holdings, share count per quarter (lines)
    04_status_distribution.png     — counts of NEW/EXIT/ADD/TRIM/HOLD vs prior quarter
    05_trajectory_distribution.png — counts of multi-quarter trajectory tags
    06_top_new_vs_exit.png         — biggest NEW positions vs biggest EXIT positions ($)

All charts use a clean, presentation-grade style (white background, restrained palette).
Designed for Obsidian Markdown embedding via ![[chart.png]] or ![](charts/chart.png).
"""

import sys
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# global presentation style
plt.rcParams.update({
    "figure.dpi": 130,
    "savefig.dpi": 130,
    "savefig.bbox": "tight",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "--",
    "font.family": ["Helvetica", "Arial", "DejaVu Sans"],
})

# restrained palette — okabe-ito + grays
PAL = {
    "primary":   "#0072B2",   # blue
    "accent":    "#D55E00",   # vermillion
    "green":     "#009E73",
    "yellow":    "#F0E442",
    "purple":    "#CC79A7",
    "lightblue": "#56B4E9",
    "gray":      "#5F6368",
    "lightgray": "#C8CCD0",
}

STATUS_COLORS = {
    "NEW":  PAL["green"],
    "ADD":  PAL["lightblue"],
    "HOLD": PAL["gray"],
    "TRIM": PAL["yellow"],
    "EXIT": PAL["accent"],
}

TRAJ_COLORS = {
    "NEW_AND_ADDING":   PAL["green"],
    "NEW_AND_HOLDING":  PAL["lightblue"],
    "NEW_AND_TRIMMING": PAL["yellow"],
    "NEW_LATEST":       PAL["primary"],
    "SCALING_UP":       PAL["green"],
    "SCALING_DOWN":     PAL["accent"],
    "HOLDING_STEADY":   PAL["gray"],
    "REVERSAL_TO_ADD":  PAL["purple"],
    "REVERSAL_TO_TRIM": PAL["yellow"],
    "EXITED":           PAL["accent"],
    "MIXED":            PAL["lightgray"],
}


def fmt_dollar_billion(x, _pos=None):
    return f"${x/1_000_000:.2f}B"


def chart_aum_history(comp, charts_dir):
    labels = comp["quarter_labels"][::-1]   # oldest → newest
    totals = comp["quarter_totals_k"][::-1] # $k
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(labels, totals, marker="o", color=PAL["primary"], linewidth=2.4, markersize=9)
    for x, y in zip(labels, totals):
        ax.annotate(f"${y/1_000_000:.2f}B", (x, y), textcoords="offset points",
                    xytext=(0, 11), ha="center", fontsize=9, color=PAL["gray"])
    ax.set_title(f"13F Reportable AUM — {comp['entity']}")
    ax.set_ylabel("Total value")
    ax.set_xlabel("Report quarter")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_dollar_billion))
    ax.set_ylim(bottom=min(totals) * 0.92, top=max(totals) * 1.08)
    fig.savefig(charts_dir / "01_aum_history.png")
    plt.close(fig)


def chart_top15_grouped(comp, charts_dir):
    rows = comp["rows"]
    top = [r for r in rows if r["latest_value"] > 0][:15]
    labels = comp["quarter_labels"][::-1]  # oldest → newest in chart
    n_q = len(labels)
    n_pos = len(top)
    if n_pos == 0:
        return

    fig, ax = plt.subplots(figsize=(11, max(4.5, 0.45 * n_pos + 1.5)))
    bar_h = 0.8 / n_q
    y_base = list(range(n_pos))[::-1]  # top of chart is rank 1

    # oldest → newest progression: light gray → light blue → primary blue
    base_palette = [PAL["lightgray"], PAL["lightblue"], PAL["primary"], PAL["accent"]]
    quarter_palette = base_palette[:n_q]

    for qi, q_label in enumerate(labels):
        vals = []
        for r in top:
            # r["quarters"] is newest → oldest; convert q_label to that order
            label_to_v = {q["label"]: q["value"] for q in r["quarters"]}
            vals.append(label_to_v.get(q_label, 0) / 1000)  # to $M
        offset = (qi - (n_q - 1) / 2) * bar_h
        ys = [y + offset for y in y_base]
        ax.barh(ys, vals, height=bar_h, color=quarter_palette[qi], label=q_label, edgecolor="white")

    ax.set_yticks(y_base)
    ax.set_yticklabels([_truncate(r["name"], 28) for r in top])
    ax.set_xlabel("Position value ($M)")
    ax.set_title(f"Top 15 Holdings (latest) — quarter-over-quarter value — {comp['entity']}")
    ax.legend(loc="lower right", frameon=False, ncols=n_q)
    fig.savefig(charts_dir / "02_top15_ribbon.png")
    plt.close(fig)


def chart_top15_share_trajectory(comp, charts_dir):
    rows = comp["rows"]
    top = [r for r in rows if r["latest_value"] > 0][:15]
    labels = comp["quarter_labels"][::-1]
    if not top:
        return

    fig, ax = plt.subplots(figsize=(11, 5.4))
    cmap = plt.colormaps.get_cmap("tab20")
    for i, r in enumerate(top):
        label_to_s = {q["label"]: q["shares"] for q in r["quarters"]}
        ys = [label_to_s.get(L, 0) / 1_000_000 for L in labels]  # to millions of shares
        ax.plot(labels, ys, marker="o", linewidth=1.8,
                color=cmap(i / 20),
                label=_truncate(r["name"], 22))
    ax.set_title(f"Top 15 — share count trajectory (M shares) — {comp['entity']}")
    ax.set_ylabel("Shares (millions)")
    ax.set_xlabel("Report quarter")
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False, fontsize=8)
    fig.savefig(charts_dir / "03_top15_share_trajectory.png")
    plt.close(fig)


def chart_status_distribution(comp, charts_dir):
    buckets = comp.get("summary_vs_prior", {})
    if not buckets:
        return
    order = ["NEW", "ADD", "HOLD", "TRIM", "EXIT"]
    labels = [k for k in order if k in buckets]
    counts = [buckets[k] for k in labels]
    colors = [STATUS_COLORS[k] for k in labels]

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    bars = ax.bar(labels, counts, color=colors, edgecolor="white")
    for b, c in zip(bars, counts):
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.2, str(c),
                ha="center", va="bottom", fontsize=10, color=PAL["gray"])
    ax.set_title("Position changes vs immediately prior quarter")
    ax.set_ylabel("Number of positions")
    ax.set_ylim(top=max(counts) * 1.18 + 1)
    fig.savefig(charts_dir / "04_status_distribution.png")
    plt.close(fig)


def chart_trajectory_distribution(comp, charts_dir):
    buckets = comp.get("trajectory_buckets", {})
    if not buckets:
        return
    items = [(k, v) for k, v in buckets.items() if k != "ABSENT"]
    items.sort(key=lambda kv: -kv[1])
    labels = [k for k, _ in items]
    counts = [v for _, v in items]
    colors = [TRAJ_COLORS.get(k, PAL["lightgray"]) for k in labels]

    fig, ax = plt.subplots(figsize=(9, max(3.5, 0.4 * len(labels) + 1)))
    y = list(range(len(labels)))[::-1]
    ax.barh(y, counts, color=colors, edgecolor="white")
    ax.set_yticks(y)
    ax.set_yticklabels([k.replace("_", " ").title() for k in labels])
    for yi, c in zip(y, counts):
        ax.text(c + 0.2, yi, str(c), va="center", fontsize=9, color=PAL["gray"])
    ax.set_title(f"Multi-quarter trajectory tags ({comp['n_quarters']} quarters)")
    ax.set_xlabel("Number of positions")
    fig.savefig(charts_dir / "05_trajectory_distribution.png")
    plt.close(fig)


def chart_top_new_vs_exit(comp, charts_dir):
    rows = comp["rows"]
    news = [r for r in rows if r["status_vs_prior"] == "NEW"]
    exits = [r for r in rows if r["status_vs_prior"] == "EXIT"]
    news.sort(key=lambda r: -r["latest_value"])
    # for exits, use prior-quarter value
    def prior_value(r):
        return r["quarters"][1]["value"] if len(r["quarters"]) > 1 else 0
    exits.sort(key=lambda r: -prior_value(r))
    n_show = min(10, max(len(news), len(exits)))
    news = news[:n_show]
    exits = exits[:n_show]

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(13, max(4, 0.4 * n_show + 2)))

    new_labels = [_truncate(r["name"], 26) for r in news][::-1]
    new_values = [r["latest_value"] / 1000 for r in news][::-1]
    if new_values:
        axL.barh(new_labels, new_values, color=PAL["green"], edgecolor="white")
        new_max = max(new_values)
        axL.set_xlim(0, new_max * 1.18)
        for i, v in enumerate(new_values):
            axL.text(v + new_max * 0.015, i, f"${v:.0f}M",
                     va="center", ha="left", fontsize=8, color=PAL["gray"])
    axL.set_title("Biggest NEW positions (latest quarter)", color=PAL["green"])
    axL.set_xlabel("Latest position value ($M)")

    ex_labels = [_truncate(r["name"], 26) for r in exits][::-1]
    ex_values = [prior_value(r) / 1000 for r in exits][::-1]
    if ex_values:
        axR.barh(ex_labels, ex_values, color=PAL["accent"], edgecolor="white")
        ex_max = max(ex_values)
        axR.set_xlim(0, ex_max * 1.18)
        for i, v in enumerate(ex_values):
            axR.text(v + ex_max * 0.015, i, f"${v:.0f}M",
                     va="center", ha="left", fontsize=8, color=PAL["gray"])
    axR.set_title("Biggest EXIT positions (size in prior quarter)", color=PAL["accent"])
    axR.set_xlabel("Prior-quarter value ($M)")

    fig.suptitle(f"NEW vs EXIT — {comp['entity']}", fontsize=13, fontweight="bold", y=1.02)
    fig.savefig(charts_dir / "06_top_new_vs_exit.png")
    plt.close(fig)


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def main():
    if len(sys.argv) < 2:
        print("Usage: visualize.py <out_dir>", file=sys.stderr)
        sys.exit(2)
    out_dir = Path(sys.argv[1])
    comp_path = out_dir / "comparison.json"
    if not comp_path.exists():
        print(f"comparison.json missing at {comp_path}", file=sys.stderr)
        sys.exit(1)
    comp = json.loads(comp_path.read_text())
    charts_dir = out_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    chart_aum_history(comp, charts_dir)
    chart_top15_grouped(comp, charts_dir)
    chart_top15_share_trajectory(comp, charts_dir)
    chart_status_distribution(comp, charts_dir)
    chart_trajectory_distribution(comp, charts_dir)
    chart_top_new_vs_exit(comp, charts_dir)

    print(f"charts written to {charts_dir}")


if __name__ == "__main__":
    main()
