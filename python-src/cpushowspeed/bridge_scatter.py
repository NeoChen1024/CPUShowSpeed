"""Scatter plot for source-linked CPU92–CPU95 overlap candidates."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

COLORS = {
    "x86": "#d95f02",
    "PA-RISC": "#1b9e77",
    "Alpha": "#7570b3",
    "SPARC": "#c51b7d",
    "MIPS": "#66a61e",
    "Other": "#555555",
}


def write_overlap_scatter(rows: list[dict[str, object]], output_dir: Path) -> dict[str, str]:
    """Show every candidate pairing while visibly grading looser matches."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    output_dir.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(10.4, 7.2))
    figure.subplots_adjust(left=0.10, right=0.97, top=0.89, bottom=0.23)

    x_max = max(float(row["cpu95_score"]) for row in rows) * 1.13
    y_max = max(float(row["cpu92_score"]) for row in rows) * 1.15
    for ratio in (30, 40, 50):
        end = min(x_max, y_max / ratio)
        axis.plot([0, end], [0, ratio * end], color="#b8b8b8", linestyle="--", linewidth=1, zorder=0)
        axis.text(end * 0.96, ratio * end * 0.96, f"{ratio}×", color="#777777", fontsize=8, ha="right", va="bottom")

    for row in sorted(rows, key=lambda item: item["plot_tier"] == "reviewed"):
        color = COLORS.get(str(row["architecture"]), COLORS["Other"])
        x = float(row["cpu95_score"])
        y = float(row["cpu92_score"])
        tier = row["plot_tier"]
        if tier == "reviewed":
            axis.scatter(x, y, s=79, marker="o", color=color, edgecolors="white", linewidths=0.8, zorder=3)
        elif tier == "relaxed_cache_agrees":
            axis.scatter(x, y, s=64, marker="s", facecolors="none", edgecolors=color, linewidths=1.5, alpha=0.6, zorder=2)
        else:
            axis.scatter(x, y, s=74, marker="x", color=color, linewidths=1.8, alpha=0.75, zorder=2)

    # Exact coordinate ties would otherwise look like one submission pairing.
    multiplicities = Counter((float(row["cpu95_score"]), float(row["cpu92_score"])) for row in rows)
    for (x, y), count in multiplicities.items():
        if count > 1:
            axis.annotate(f"×{count}", (x, y), xytext=(8, 7), textcoords="offset points", fontsize=8, color="#333333")

    axis.set_xlim(0, x_max)
    axis.set_ylim(0, y_max)
    axis.set_xlabel("SPECint95 (reported peak score)")
    axis.set_ylabel("SPECint92 (VAX-relative reported peak score)")
    axis.set_title(f"CPU92–CPU95 overlap: all {len(rows)} candidate pairings")
    axis.grid(alpha=0.18)
    axis.set_axisbelow(True)
    tiers = [
        Line2D(
            [],
            [],
            marker="o",
            linestyle="None",
            markerfacecolor="#555555",
            markeredgecolor="white",
            markersize=9,
            label="Reviewed configuration-near",
        ),
        Line2D(
            [],
            [],
            marker="s",
            linestyle="None",
            markerfacecolor="none",
            markeredgecolor="#555555",
            markersize=8,
            label="Relaxed; cache capacity agrees",
        ),
        Line2D([], [], marker="x", linestyle="None", color="#555555", markersize=9, label="Relaxed; cache differs/unclear"),
    ]
    first = axis.legend(handles=tiers, loc="upper left", title="Match tier", framealpha=0.93, fontsize=8)
    axis.add_artist(first)
    families = sorted(
        {str(row["architecture"]) for row in rows}, key=lambda name: list(COLORS).index(name) if name in COLORS else 99
    )
    handles = [
        Line2D([], [], marker="o", linestyle="None", color=COLORS.get(name, COLORS["Other"]), markersize=7, label=name)
        for name in families
    ]
    axis.legend(handles=handles, loc="lower right", title="Processor family", framealpha=0.93, fontsize=8)
    counts = {
        name: sum(row["plot_tier"] == name for row in rows)
        for name in ("reviewed", "relaxed_cache_agrees", "relaxed_cache_differs_or_unclear")
    }
    figure.text(
        0.5,
        0.07,
        f"{len(rows)} candidate pairings: {counts['reviewed']} reviewed, "
        f"{counts['relaxed_cache_agrees']} relaxed with matching cache capacities, "
        f"{counts['relaxed_cache_differs_or_unclear']} with differing/unclear cache.\n"
        "Repeated submissions remain visible and can form multiple pairings; points are not independent. Gray guides are not fitted factors.",
        ha="center",
        va="bottom",
        fontsize=8,
        color="#444444",
    )
    png = output_dir / "cpu92-cpu95-overlap-scatter.png"
    svg = output_dir / "cpu92-cpu95-overlap-scatter.svg"
    figure.savefig(png, dpi=180)
    figure.savefig(svg)
    plt.close(figure)
    return {"png": str(png), "svg": str(svg)}
