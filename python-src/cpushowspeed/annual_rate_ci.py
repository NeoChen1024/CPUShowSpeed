"""Annual rate distributions with coherent calibration-bootstrap overlays."""

from __future__ import annotations

import csv
import json
import textwrap
from collections import defaultdict
from pathlib import Path

import click
import numpy as np
from cpushowspeed.annual_rate import _annual, _sha256, _si, collect_annual_records
from cpushowspeed.curated import DATABASE

METHOD_VERSION = "annual-rate-combined-ci-v1"


def year_draws(rows: list[dict], leader: dict, draws: np.ndarray, generations: list[str]) -> dict[str, np.ndarray]:
    """One calibration vector per replicate, shared by all rows in a generation."""
    scores = np.asarray([float(row["reported_score"]) for row in rows])
    indices = np.asarray([generations.index(str(row["generation"])) for row in rows])
    output = {name: np.empty(len(draws)) for name in ("q1", "median", "q3", "frontier")}
    for start in range(0, len(draws), 128):
        stop = min(start + 128, len(draws))
        values = draws[start:stop, indices] * scores
        quantiles = np.quantile(values, [0.25, 0.5, 0.75], axis=1, method="linear")
        for index, name in enumerate(("q1", "median", "q3")):
            output[name][start:stop] = quantiles[index]
        output["frontier"][start:stop] = values.max(axis=1)
    output["fixed_leader"] = draws[:, generations.index(str(leader["generation"]))] * float(leader["reported_score"])
    return output


def _plot(rows: list[dict], leaders: list[dict], stats: list[dict], mode: str, output_dir: Path) -> dict:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch, Rectangle
    from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

    selected = [row for row in leaders if row["mode"] == mode]
    summary = {int(row["year"]): row for row in stats if row["mode"] == mode}
    groups = defaultdict(list)
    for row in rows:
        if row["mode"] == mode and row["year"]:
            groups[int(row["year"])].append(float(row["vaxen_same_os"]))
    fig, (names, counts, axis) = plt.subplots(
        1,
        3,
        figsize=(19, len(selected) * 0.61 + 2.0),
        sharey=True,
        gridspec_kw={"width_ratios": [5.5, 0.55, 9]},
        layout="constrained",
    )
    for label_axis in (names, counts):
        label_axis.set_xlim(0, 1)
        label_axis.axis("off")
    names.set_title("Year / highest-scoring System / CPU", loc="left", fontsize=10)
    counts.set_title("n", fontsize=10)
    axis.set_title("Annual submissions and calibration uncertainty", fontsize=10)
    axis.set_xscale("log")
    axis.xaxis.set_major_locator(LogLocator(base=10))
    axis.xaxis.set_minor_locator(LogLocator(base=10, subs=(2, 5)))
    axis.xaxis.set_minor_formatter(NullFormatter())
    axis.xaxis.set_major_formatter(FuncFormatter(lambda value, _: _si(value)))
    axis.grid(axis="x", which="major", alpha=0.22)
    axis.grid(axis="x", which="minor", alpha=0.07)
    axis.set_yticks([])
    axis.set_ylim(len(selected) - 0.35, -0.75)
    axis.set_xlim(
        min(min(values) for values in groups.values()) / 1.4, max(float(row["fixed_leader_high"]) for row in summary.values()) * 3
    )
    for y, leader in enumerate(selected):
        year = int(leader["year"])
        stat = summary[year]
        values = np.asarray(groups[year])
        q1, med, q3 = np.quantile(values, [0.25, 0.5, 0.75])
        iqr = q3 - q1
        whisker_low = float(values[values >= q1 - 1.5 * iqr].min())
        whisker_high = float(values[values <= q3 + 1.5 * iqr].max())
        low, high = float(stat["q1_low"]), float(stat["q3_high"])
        axis.add_patch(Rectangle((low, y - 0.29), high - low, 0.58, color="#3685ae", alpha=0.14, linewidth=0))
        # Intervals for each quartile boundary remain individually inspectable.
        for label in ("q1", "median", "q3"):
            axis.plot(
                [stat[label + "_low"], stat[label + "_high"]], [y + 0.24, y + 0.24], color="#3685ae", alpha=0.65, linewidth=1.5
            )
        axis.bxp(
            [
                {
                    "med": med,
                    "q1": q1,
                    "q3": q3,
                    "whislo": whisker_low,
                    "whishi": whisker_high,
                    "fliers": values[(values < whisker_low) | (values > whisker_high)].tolist(),
                }
            ],
            positions=[y],
            vert=False,
            widths=0.24,
            patch_artist=True,
            manage_ticks=False,
            boxprops={"facecolor": "#a7c8d9", "edgecolor": "#366985"},
            medianprops={"color": "#194862", "linewidth": 1.5},
            whiskerprops={"color": "#738795", "linewidth": 0.7},
            capprops={"color": "#738795", "linewidth": 0.7},
            flierprops={"marker": ".", "markersize": 2, "markeredgewidth": 0, "markerfacecolor": "#788793", "alpha": 0.22},
        )
        leader_low, leader_high = float(stat["fixed_leader_low"]), float(stat["fixed_leader_high"])
        axis.add_patch(Rectangle((leader_low, y - 0.23), leader_high - leader_low, 0.46, color="#df8b3b", alpha=0.23, linewidth=0))
        dot = axis.scatter(float(leader["vaxen"]), y, s=19, c="#bd6028", zorder=5)
        dot.set_url(str(leader["source_url"]))
        score_label = _si(float(leader["vaxen"]))
        if float(stat["leader_top_fraction"]) < 0.95:
            score_label += f"\n(top {100 * float(stat['leader_top_fraction']):.1f}%)"
        axis.text(leader_high * 1.09, y, score_label, fontsize=8, va="center", color="#7e421e")
        title = f"{year} [{str(leader['generation']).upper()}] {leader['system']}"
        wrapped = textwrap.wrap(title, width=65, max_lines=2, placeholder="…")
        cpu = textwrap.shorten(f"CPU: {leader['processor']}", width=72, placeholder="…")
        label = names.text(0, y, "\n".join([*wrapped, cpu]), fontsize=8.0, va="center", linespacing=1.15)
        label.set_url(str(leader["source_url"]))
        counts.text(0.5, y, str(len(values)), fontsize=8, ha="center", va="center")
        for pane in (names, counts, axis):
            pane.axhline(y + 0.5, linewidth=0.5, color="#dbe2e7", zorder=0)
    axis.set_xlabel("Estimated integer-rate throughput (VAXen; logarithmic scale)")
    fig.suptitle(
        f"SPEC integer-rate annual distributions and representative hardware — {mode}\n"
        "Reported hardware-availability year · all positive dated submissions · same-OS CPU92 anchor",
        fontsize=14,
    )
    fig.legend(
        handles=[
            Patch(facecolor="#a7c8d9", edgecolor="#366985", label="Central IQR; line = median; whiskers = 1.5 IQR"),
            Patch(facecolor="#3685ae", alpha=0.14, label="Quartile CI envelope (Q1 lower to Q3 upper)"),
            Line2D([], [], color="#3685ae", label="95% CI of Q1 / median / Q3 below each box"),
            Line2D([], [], color="#bd6028", marker="o", linestyle="None", label="Central highest submission"),
            Patch(facecolor="#df8b3b", alpha=0.23, label="Fixed representative's 95% calibration CI"),
        ],
        loc="outside lower center",
        ncol=2,
        fontsize=9,
    )
    paths = {}
    for suffix in ("png", "svg"):
        path = output_dir / f"annual-rate-combined-{mode}.{suffix}"
        fig.savefig(path, dpi=165 if suffix == "png" else None)
        paths[suffix] = str(path)
    plt.close(fig)
    return paths


def analyze(database: Path, research_dir: Path, fit_dir: Path, output_dir: Path, summary_dir: Path) -> dict:
    records, provenance = collect_annual_records(database, research_dir, fit_dir)
    leaders, _ = _annual(records, "same_os")
    metadata_path = fit_dir / "integer-rate-chain-bootstrap.json"
    metadata = json.loads(metadata_path.read_text())
    for path, digest in metadata["inputs_sha256"].items():
        if _sha256(Path(path)) != digest:
            raise ValueError(f"stale chain bootstrap input: {path}; rerun bootstrap-rate-chain")
    if metadata["database_inputs_sha256"] != provenance["inputs_sha256"]:
        raise ValueError("chain bootstrap used another database; rerun bootstrap-rate-chain")
    draws_path = fit_dir / "integer-rate-chain-bootstrap.npz"
    if _sha256(draws_path) != metadata["draws_sha256"]:
        raise ValueError("chain bootstrap array hash mismatch")
    with np.load(draws_path, allow_pickle=False) as arrays:
        generations = list(arrays["generations"])
        modes = list(arrays["modes"])
        scenario = list(arrays["scenarios"]).index("same_os")
        draws = arrays["vaxen_per_rate_score"][scenario].copy()
    if not np.isfinite(draws).all() or (draws <= 0).any():
        raise ValueError("invalid chain multipliers")
    groups = defaultdict(list)
    for row in records:
        if row["year"]:
            groups[str(row["mode"]), int(row["year"])].append(row)
    summaries = []
    for leader in leaders:
        mode, year = str(leader["mode"]), int(leader["year"])
        cohort = groups[mode, year]
        click.echo(f"Propagating {mode} {year}: {len(cohort)} submissions", err=True)
        samples = year_draws(cohort, leader, draws[modes.index(mode)], generations)
        central = np.asarray([float(row["vaxen_same_os"]) for row in cohort])
        row = {
            "method_version": METHOD_VERSION,
            "mode": mode,
            "year": year,
            "submission_count": len(cohort),
            "scenario": "same_os",
            "bootstrap_replicates": len(draws[0]),
            "q1_central": float(np.quantile(central, 0.25)),
            "median_central": float(np.median(central)),
            "q3_central": float(np.quantile(central, 0.75)),
            "leader_central": float(leader["vaxen"]),
            "leader_source_url": leader["source_url"],
        }
        for name, values in samples.items():
            low, high = np.quantile(values, [0.025, 0.975], method="linear")
            row[name + "_low"], row[name + "_high"] = float(low), float(high)
        row["leader_top_fraction"] = float(np.mean(np.isclose(samples["fixed_leader"], samples["frontier"], rtol=1e-12, atol=0)))
        row["chain_draws_sha256"] = metadata["draws_sha256"]
        row["uncertainty_scope"] = "pointwise_conditional_calibration_only"
        summaries.append(row)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)
    csv_path = summary_dir / "annual-rate-confidence.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(summaries)
    figures = {}
    for mode in modes:
        figures[mode] = _plot(records, leaders, summaries, mode, output_dir)
    result = {
        "method_version": METHOD_VERSION,
        "confidence_csv": str(csv_path),
        "figures": figures,
        "bootstrap_replicates": len(draws[0]),
        "chain_draws_sha256": metadata["draws_sha256"],
        "year_mode_rows": len(summaries),
        "minimum_top_retention": min(row["leader_top_fraction"] for row in summaries),
        **provenance,
    }
    (output_dir / "annual-rate-confidence-summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


@click.command("annual-rate-ci")
@click.option("--database", type=click.Path(path_type=Path, dir_okay=False), default=DATABASE, show_default=True)
@click.option("--research-dir", type=click.Path(path_type=Path), default=Path("research/data/spec/fitting"), show_default=True)
@click.option("--fit-dir", type=click.Path(path_type=Path), default=Path("data/derived/spec/fitting"), show_default=True)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/figures/annual-rate"), show_default=True)
@click.option("--summary-dir", type=click.Path(path_type=Path), default=Path("research/data/spec"), show_default=True)
def annual_rate_ci_command(database: Path, research_dir: Path, fit_dir: Path, output_dir: Path, summary_dir: Path) -> None:
    """Combine annual rate boxes, representative hardware and calibration CIs."""
    try:
        result = analyze(database, research_dir, fit_dir, output_dir, summary_dir)
    except (OSError, ValueError, KeyError, IndexError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, sort_keys=True))
