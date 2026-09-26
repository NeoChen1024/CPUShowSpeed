"""Source-linked SPEC89 to CPU92 scatter plot from the curated bridge table."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path

import click
from cpushowspeed.spec89 import DEFAULT_SNAPSHOT, verify_snapshot

FIELDS = (
    "bridge_id",
    "record_id",
    "source_id",
    "system",
    "x_metric",
    "x_score",
    "y_metric",
    "y_score",
    "bridge_type",
    "measurement_type",
    "source_kind",
    "coordinate_multiplicity",
    "source_url",
    "page_table",
    "source_date",
    "source_message_id",
    "source_file",
    "source_lines",
)


def _positive(value: str, field: str, bridge_id: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"missing or invalid {field} in {bridge_id}") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"non-positive {field} in {bridge_id}")
    return number


def read_bridge_pairs(snapshot: Path) -> list[dict[str, object]]:
    """Preserve each cited bridge row and keep integer and composite metrics distinct."""
    with (snapshot / "csv" / "aggregate89.csv").open(newline="", encoding="utf-8-sig") as stream:
        aggregate = {row["record_id"]: row for row in csv.DictReader(stream)}
    with (snapshot / "csv" / "bridges89_92.csv").open(newline="", encoding="utf-8-sig") as stream:
        bridges = list(csv.DictReader(stream))
    if not bridges:
        raise ValueError("SPEC89–CPU92 bridge table is empty")

    records: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in bridges:
        bridge_id = row["bridge_id"]
        if bridge_id in seen:
            raise ValueError(f"duplicate bridge ID: {bridge_id}")
        seen.add(bridge_id)
        source_record = aggregate.get(row["record_id"])
        if source_record is None or source_record["source_id"] != row["source_id"]:
            raise ValueError(f"bridge source record mismatch: {bridge_id}")
        direct = row["bridge_type"] == "full_INT_FP_89_92"
        if not direct and row["bridge_type"] != "mark89_to_INT_FP_92":
            raise ValueError(f"unknown bridge type: {bridge_id}")
        x_metric = "SPECint89" if direct else "SPECmark89"
        if direct and not row["SPECfp89"]:
            raise ValueError(f"full bridge lacks SPECfp89: {bridge_id}")
        if not direct and row["SPECint89"]:
            raise ValueError(f"mark-only bridge unexpectedly reports SPECint89: {bridge_id}")
        for metric in ("SPECmark89", "SPECint89", "SPECfp89"):
            if row[metric] != source_record[metric]:
                raise ValueError(f"bridge and aggregate {metric} disagree: {bridge_id}")
        x = _positive(row[x_metric], x_metric, bridge_id)
        y = _positive(row["SPECint92"], "SPECint92", bridge_id)
        records.append(
            {
                "bridge_id": bridge_id,
                "record_id": row["record_id"],
                "source_id": row["source_id"],
                "system": row["system"],
                "x_metric": x_metric,
                "x_score": x,
                "y_metric": "SPECint92",
                "y_score": y,
                "bridge_type": row["bridge_type"],
                "measurement_type": row["measurement_type"],
                "source_kind": "saved Usenet" if row["source_file"] else "cited report",
                "coordinate_multiplicity": 0,
                "source_url": row["source_url"],
                "page_table": row["page_table"],
                "source_date": row["source_date"],
                "source_message_id": row["source_message_id"],
                "source_file": row["source_file"],
                "source_lines": row["source_lines"],
            }
        )
    multiplicities = Counter((record["x_metric"], record["x_score"], record["y_score"]) for record in records)
    for record in records:
        record["coordinate_multiplicity"] = multiplicities[record["x_metric"], record["x_score"], record["y_score"]]
    return records


def write_scatter(records: list[dict[str, object]], output_dir: Path) -> dict[str, object]:
    """Write the plotted records and a two-panel figure without fitting a conversion."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "spec89-cpu92-bridge-records.csv"
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)

    figure, axes = plt.subplots(1, 2, figsize=(12.2, 6.3))
    figure.subplots_adjust(left=0.08, right=0.98, top=0.85, bottom=0.25, wspace=0.25)
    panels = (
        ("SPECint89", "Integer to integer", axes[0]),
        ("SPECmark89", "Composite mark to integer", axes[1]),
    )
    colors = {"cited report": "#2878a9", "saved Usenet": "#d77426"}
    for metric, title, axis in panels:
        group = [record for record in records if record["x_metric"] == metric]
        for record in group:
            color = colors[record["source_kind"]]
            marker = "D" if record["measurement_type"] == "reported_development" else "o"
            axis.scatter(
                record["x_score"],
                record["y_score"],
                marker=marker,
                s=69 if marker == "D" else 59,
                facecolors="none" if marker == "D" else color,
                edgecolors=color,
                linewidths=1.5,
                alpha=0.8,
                zorder=3,
            )
        counts = Counter((record["x_score"], record["y_score"]) for record in group)
        for (x, y), count in counts.items():
            if count > 1:
                axis.annotate(f"×{count}", (x, y), xytext=(7, 6), textcoords="offset points", fontsize=8, color="#444444")
        axis.set_xlim(0, max(float(record["x_score"]) for record in group) * 1.16)
        axis.set_ylim(0, max(float(record["y_score"]) for record in group) * 1.18)
        axis.set_title(f"{title} · {len(group)} rows", fontsize=11)
        axis.set_xlabel(f"{metric} (reported score)")
        axis.set_ylabel("SPECint92 (reported score)")
        axis.grid(alpha=0.2)
        axis.set_axisbelow(True)
        if metric == "SPECint89":
            end = min(*axis.get_xlim()[1:], axis.get_ylim()[1])
            axis.plot([0, end], [0, end], linestyle="--", linewidth=1, color="#999999", zorder=1)
            axis.text(end * 0.97, end * 0.97, "equal numbers", color="#777777", ha="right", va="bottom", fontsize=8)

    legend = [
        Line2D([], [], marker="o", linestyle="None", color=colors["cited report"], markersize=7, label="Cited report"),
        Line2D([], [], marker="o", linestyle="None", color=colors["saved Usenet"], markersize=7, label="Saved Usenet"),
        Line2D(
            [],
            [],
            marker="D",
            linestyle="None",
            markerfacecolor="none",
            markeredgecolor="#444444",
            markersize=7,
            label="Development-level",
        ),
    ]
    figure.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, 0.93), ncol=3, frameon=False, fontsize=9)
    figure.suptitle("SPEC89 → CPU92: source-paired published scores", fontsize=15, y=0.99)
    figure.text(
        0.5,
        0.06,
        "All 34 source rows are retained; ×N marks coincident coordinates, including republications.\n"
        "The panels use different 1989 metrics. These points are not independent runs or a fitted cross-suite conversion.",
        ha="center",
        fontsize=8,
        color="#444444",
    )
    png_path = output_dir / "spec89-cpu92-bridge-scatter.png"
    svg_path = output_dir / "spec89-cpu92-bridge-scatter.svg"
    figure.savefig(png_path, dpi=180)
    figure.savefig(svg_path)
    plt.close(figure)
    return {
        "records": str(csv_path),
        "png": str(png_path),
        "svg": str(svg_path),
        "source_rows": len(records),
        "integer_pairs": sum(record["x_metric"] == "SPECint89" for record in records),
        "mark_only_pairs": sum(record["x_metric"] == "SPECmark89" for record in records),
        "development_rows": sum(record["measurement_type"] == "reported_development" for record in records),
    }


@click.command("spec89-92")
@click.option("--snapshot", type=click.Path(path_type=Path), default=DEFAULT_SNAPSHOT, show_default=True)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/figures"), show_default=True)
def spec89_92_command(snapshot: Path, output_dir: Path) -> None:
    """Plot all source-paired SPEC89/CPU92 scores in distinct metric panels."""
    try:
        verify_snapshot(snapshot)
        result = write_scatter(read_bridge_pairs(snapshot), output_dir)
    except (OSError, ValueError, AssertionError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, sort_keys=True))
