#!/usr/bin/env python3
"""
visual_report.py — Bonus visual report generator using matplotlib.
Generates bar charts, pie charts, and timeline plots from log data.
"""

import sys
from pathlib import Path
from collections import Counter

try:
    import matplotlib
    matplotlib.use("Agg")          # non-interactive backend (no display needed)
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.gridspec as gridspec
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


COLORS = {
    "ERROR":   "#e74c3c",
    "WARNING": "#f39c12",
    "INFO":    "#3498db",
    "DEBUG":   "#95a5a6",
    "UNKNOWN": "#bdc3c7",
}


def _check_matplotlib():
    if not HAS_MATPLOTLIB:
        print("  matplotlib not installed. Run:  pip install matplotlib")
        return False
    return True


def generate_visual_report(entries, stats: dict, output_path: str = "reports/visual_report.png"):
    """
    Create a multi-panel PNG report:
      - Pie chart  : log level distribution
      - Bar chart  : hourly activity
      - Bar chart  : errors vs warnings by date
      - Text panel : key KPIs
    """
    if not _check_matplotlib():
        return None

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(16, 10), facecolor="#1a1a2e")
    fig.suptitle("System Log Analysis Report", fontsize=18, fontweight="bold",
                 color="white", y=0.98)

    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.35)

    # ── Panel 1: Pie chart — level distribution ──────────────────────
    ax_pie = fig.add_subplot(gs[0, 0])
    level_data = {
        k: v for k, v in stats["level_counts"].items()
        if k in COLORS and v > 0
    }
    if level_data:
        wedge_colors = [COLORS.get(k, "#bdc3c7") for k in level_data]
        wedges, texts, autotexts = ax_pie.pie(
            level_data.values(),
            labels=level_data.keys(),
            colors=wedge_colors,
            autopct="%1.1f%%",
            startangle=140,
            textprops={"color": "white", "fontsize": 9},
            wedgeprops={"edgecolor": "#1a1a2e", "linewidth": 1.5},
        )
        for at in autotexts:
            at.set_fontsize(8)
    ax_pie.set_facecolor("#16213e")
    ax_pie.set_title("Log Level Distribution", color="white", fontsize=11, pad=10)

    # ── Panel 2: Hourly activity bar ─────────────────────────────────
    ax_hour = fig.add_subplot(gs[0, 1:])
    hourly = stats.get("hourly_counts", {})
    if hourly:
        hours  = list(range(24))
        counts = [hourly.get(h, 0) for h in hours]
        bar_colors = ["#e74c3c" if c == max(counts) else "#3498db" for c in counts]
        bars = ax_hour.bar(hours, counts, color=bar_colors, edgecolor="#1a1a2e", linewidth=0.5)
        ax_hour.set_xlabel("Hour of Day", color="white", fontsize=9)
        ax_hour.set_ylabel("Log Entries", color="white", fontsize=9)
        ax_hour.set_xticks(hours)
        ax_hour.set_xticklabels([f"{h:02d}" for h in hours], fontsize=7, color="#aaaaaa")
        ax_hour.tick_params(axis="y", colors="#aaaaaa")
    ax_hour.set_facecolor("#16213e")
    ax_hour.set_title("Hourly Activity", color="white", fontsize=11)
    ax_hour.spines[:].set_color("#333366")

    # ── Panel 3: Stacked bar — errors & warnings by date ─────────────
    ax_date = fig.add_subplot(gs[1, :2])
    dates = sorted(stats.get("date_counts", {}).keys())
    if dates:
        lbd   = stats.get("level_by_date", {})
        errs  = [lbd.get(d, {}).get("ERROR",   0) for d in dates]
        warns = [lbd.get(d, {}).get("WARNING",  0) for d in dates]
        infos = [lbd.get(d, {}).get("INFO",     0) for d in dates]
        x = range(len(dates))
        ax_date.bar(x, errs,  label="ERROR",   color=COLORS["ERROR"],   width=0.55)
        ax_date.bar(x, warns, label="WARNING", color=COLORS["WARNING"], width=0.55,
                    bottom=errs)
        ax_date.bar(x, infos, label="INFO",    color=COLORS["INFO"],    width=0.55,
                    bottom=[e + w for e, w in zip(errs, warns)])
        ax_date.set_xticks(list(x))
        ax_date.set_xticklabels(dates, rotation=20, ha="right", fontsize=8, color="#aaaaaa")
        ax_date.tick_params(axis="y", colors="#aaaaaa")
        ax_date.legend(facecolor="#16213e", edgecolor="#333366",
                       labelcolor="white", fontsize=8)
    ax_date.set_facecolor("#16213e")
    ax_date.set_title("Errors & Warnings by Date", color="white", fontsize=11)
    ax_date.spines[:].set_color("#333366")
    ax_date.set_xlabel("Date", color="white", fontsize=9)
    ax_date.set_ylabel("Count", color="white", fontsize=9)

    # ── Panel 4: KPI text panel ───────────────────────────────────────
    ax_kpi = fig.add_subplot(gs[1, 2])
    ax_kpi.set_facecolor("#16213e")
    ax_kpi.axis("off")
    ax_kpi.set_title("Key Metrics", color="white", fontsize=11)

    kpis = [
        ("Total Entries",  str(stats["total"])),
        ("Errors",         str(stats["level_counts"].get("ERROR",   0))),
        ("Warnings",       str(stats["level_counts"].get("WARNING", 0))),
        ("Info",           str(stats["level_counts"].get("INFO",    0))),
        ("Error Rate",     f"{stats['error_rate']}%"),
        ("Critical Events", str(len(stats.get("critical_entries", [])))),
        ("Period Start",   stats["time_range"]["start"][:10]),
        ("Period End",     stats["time_range"]["end"][:10]),
    ]

    for idx, (label, value) in enumerate(kpis):
        y_pos = 0.92 - idx * 0.115
        ax_kpi.text(0.02, y_pos, label + ":", transform=ax_kpi.transAxes,
                    fontsize=9, color="#aaaaaa", va="top")
        ax_kpi.text(0.98, y_pos, value, transform=ax_kpi.transAxes,
                    fontsize=10, color="white", va="top", ha="right", fontweight="bold")
        ax_kpi.plot([0.02, 0.98], [y_pos - 0.04, y_pos - 0.04],
                    transform=ax_kpi.transAxes,
                    color="#333366", linewidth=0.5)

    # ── Footer ────────────────────────────────────────────────────────
    from datetime import datetime
    fig.text(0.5, 0.01,
             f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | System Log Analyzer v1.0",
             ha="center", fontsize=8, color="#555577")

    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return str(Path(output_path).resolve())


if __name__ == "__main__":
    # Quick self-test when run directly
    print("visual_report module loaded. Import and call generate_visual_report().")
