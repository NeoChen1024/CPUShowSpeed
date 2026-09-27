"""Exploratory classical-workload / SPEC92 rate associations; no chain update."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import click
from cpushowspeed.calibration import ANCHOR, fit
from cpushowspeed.calibration import quantile as quantile
from cpushowspeed.classic_values import linpack_n100, numeric
from cpushowspeed.research_io import code_hashes, write_csv

METRICS = {
    "Dhrystone": [("v1.1_DMIPS", "Dhrystone 1.1 (DMIPS)"), ("v2.1_DMIPS", "Dhrystone 2.1 (DMIPS)")],
    "Whetstone": [("MWIPS", "Whetstone Fortran, native precision (MWIPS)"), ("MWIPS_DP", "Whetstone Fortran, DP (MWIPS)")],
    "LINPACK": [("n100_MFLOPS", "LINPACK n=100 (MFLOPS)")],
}
SCENARIOS = ("clock_known_single_cpu", "clock_unknown_allowed_single_cpu")


def pair_rows(pairs, classical, specs, pages):
    rows = []
    for pair in pairs:
        c, s = classical[pair["classic_id"]], specs[pair["spec_id"]]
        if not pair["spec_cohort"].startswith("SPEC92"):
            continue
        for metric, label in METRICS.get(c["benchmark"], []):
            x = linpack_n100(c, pages) if metric == "n100_MFLOPS" else numeric(c["metrics_raw"].get(metric, ""))
            for variant, target in (("base", "SPECrate_base_int92"), ("peak", "SPECrate_int92")):
                y = numeric(s["metrics_raw"].get(target, ""))
                for scenario in SCENARIOS:
                    reasons = []
                    if x is None:
                        reasons.append("classical_metric_missing_or_unparsed")
                    if y is None:
                        reasons.append("spec_metric_missing")
                    if numeric(s.get("cpu_count", "")) != 1:
                        reasons.append("spec_cpu_count_not_one")
                    count = c.get("reported_processor_count")
                    if count is not None and numeric(count) != 1:
                        reasons.append("classical_processor_count_not_one")
                    if pair["clock_check"] == "conflict":
                        reasons.append("known_clock_conflict")
                    elif scenario == SCENARIOS[0] and pair["clock_check"] != "compatible_1pct":
                        reasons.append("clock_unknown")
                    if c["benchmark"] == "Whetstone" and c.get("language_raw") != "For":
                        reasons.append("outside_fortran_cohort")
                    rows.append(
                        dict(
                            pair,
                            metric=metric,
                            label=label,
                            variant=variant,
                            scenario=scenario,
                            x=x,
                            spec_score=y,
                            y_vaxen=y * ANCHOR if y else None,
                            included=not reasons,
                            exclusion_reasons=";".join(reasons),
                            classical_source_blake3=c["source_blake3"],
                            classical_raw=c["raw_record"],
                            spec_raw=json.dumps(s["raw_record"], sort_keys=True),
                            warning="unverified_configuration;classical_concurrency_not_established;conditional_exploratory_fit",
                        )
                    )
    return rows


def plots(output, rows, summaries):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import LogLocator, NullFormatter

    metrics = [x for group in METRICS.values() for x in group]
    for variant in ("base", "peak"):
        fig, axes = plt.subplots(2, 3, figsize=(17, 10))
        for ax, (metric, label) in zip(axes.flat, metrics):
            selected = [r for r in rows if r["variant"] == variant and r["metric"] == metric]
            excluded = [r for r in selected if r["scenario"] == SCENARIOS[1] and not r["included"] and r["x"] and r["y_vaxen"]]
            ax.scatter([r["x"] for r in excluded], [r["y_vaxen"] for r in excluded], c="0.8", marker="x", s=22)
            for scenario, color in zip(reversed(SCENARIOS), ("#e58b28", "#1875aa")):
                data = [r for r in selected if r["scenario"] == scenario and r["included"]]
                summary = next(
                    s for s in summaries if s["variant"] == variant and s["metric"] == metric and s["scenario"] == scenario
                )
                ax.scatter([r["x"] for r in data], [r["y_vaxen"] for r in data], color=color, s=25, alpha=0.55)
                if data and "factor" in summary:
                    xx = [min(r["x"] for r in data) * 0.85, max(r["x"] for r in data) * 1.15]
                    ax.plot(xx, [x * summary["factor"] for x in xx], color=color)
                    ax.fill_between(
                        xx,
                        [x * summary["factor_ci95_low"] for x in xx],
                        [x * summary["factor_ci95_high"] for x in xx],
                        color=color,
                        alpha=0.12,
                    )
                short = "known clocks" if scenario == SCENARIOS[0] else "unknown allowed"
                ax.plot([], [], color=color, label=f"{short}: {summary['models']} models / {summary['pairs']} pairs")
            ax.set(xscale="log", yscale="log", xlabel=label, ylabel="SPEC92 integer-rate (estimated VAXen)")
            ax.xaxis.set_major_locator(LogLocator(base=10, subs=(1, 2, 5)))
            ax.xaxis.set_minor_formatter(NullFormatter())
            ax.grid(alpha=0.15, which="both")
            ax.legend(fontsize=8)
        axes.flat[-1].axis("off")
        axes.flat[-1].text(
            0,
            0.9,
            "Exploratory candidate-cohort fits\n\nLine: model-balanced geometric ratio\nShading: conditional factor CI95\nGray crosses: numeric excluded pairs\n\nAll repeated source rows retained.\nOverlapping points may hide repetitions.\nSPEC endpoint: one reported CPU.\nClassical concurrency is not established.\n\nFP-heavy workloads vs integer rate:\nassociation diagnostics, not a universal conversion.\n\nNo SPEC89 or modern rate-chain update.",
            va="top",
            fontsize=11,
        )
        fig.suptitle(
            f"Classical benchmarks vs SPEC92 integer rate — {variant}\nCandidate models; bootstrap intervals omit configuration/source mismatch",
            fontsize=14,
        )
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        for suffix in ("png", "svg"):
            fig.savefig(output / f"classic-spec92-{variant}.{suffix}", dpi=160)
        plt.close(fig)


@click.command("fit-spec92")
@click.option(
    "--input-root",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/overlap-spec"),
    show_default=True,
)
@click.option(
    "--linpack-text",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/netlib-linpack-report.txt"),
    show_default=True,
)
@click.option("--output", type=click.Path(path_type=Path), default=Path("data/derived/classic/fit-spec92"), show_default=True)
@click.option("--bootstrap", type=click.IntRange(min=100), default=10000, show_default=True)
@click.option("--seed", type=int, default=20260926, show_default=True)
def fit_spec92(input_root, linpack_text, output, bootstrap, seed):
    """Fit candidate model cohorts; keep all exclusions and leave the rate chain unchanged."""
    paths = [input_root / name for name in ("classical-records.jsonl", "spec-records.jsonl", "candidate-pairs.csv")]
    classical, specs = [{r["id"]: r for r in map(json.loads, p.read_text().splitlines())} for p in paths[:2]]
    with paths[2].open(newline="") as f:
        pairs = list(csv.DictReader(f))
    rows = pair_rows(pairs, classical, specs, linpack_text.read_text().split("\f"))
    summaries = []
    for family, metrics in METRICS.items():
        for metric, label in metrics:
            for variant in ("base", "peak"):
                for scenario in SCENARIOS:
                    selected = [
                        r
                        for r in rows
                        if r["metric"] == metric and r["variant"] == variant and r["scenario"] == scenario and r["included"]
                    ]
                    summaries.append(
                        dict(benchmark=family, metric=metric, variant=variant, scenario=scenario, **fit(selected, bootstrap, seed))
                    )
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "pairs.csv", rows)
    write_csv(output / "summary.csv", summaries)
    plots(output, rows, summaries)
    audit = dict(
        method="classic-spec92-candidate-fit-v1",
        anchor=ANCHOR,
        bootstrap=bootstrap,
        seed=seed,
        uncertainty="model cluster percentile bootstrap; conditional on unverified cohort; not prediction intervals",
        input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths + [linpack_text]},
        implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        exclusions=dict(Counter(reason for r in rows for reason in r["exclusion_reasons"].split(";") if reason)),
        output_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.glob("*.csv"))},
    )
    audit["shared_code_sha256"] = code_hashes(Path(__file__))
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps({"output": str(output), "fits": len(summaries), "pair_metric_scenarios": len(rows)}))
