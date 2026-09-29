"""Separate speed calibration and speed/rate diagnostics from cached evidence."""

import hashlib
import json
import math
import re
import statistics
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import click
import numpy as np
from cpushowspeed.research_io import code_hashes, write_csv
from cpushowspeed.spec92_rate import BENCHMARKS, _checked, _optional, _required, _text
from cpushowspeed.spec92_rate_fit import collect_cpu92_rate
from cpushowspeed.spec_inputs import collect_speed92, parse_speed92
from cpushowspeed.spec_overlap import (
    Result,
    _automatic_pairs,
    _checked_bulk,
    _frequency,
    _memory_mib,
    _normalized,
    _processor_key,
    _statistics,
)
from cpushowspeed.spec_rate_chain import configuration_logs
from cpushowspeed.spec_rate_fit import GENERATIONS, MODES, collect_integer

METHOD = "spec-dual-track-v1"


def chain_intervals(pairs, draws=10000, seed=892026):
    """Resample shared configuration keys once per replicate across all edges."""
    generations = ("cpu92", *GENERATIONS)
    rows, arrays = [], {}
    for mode in MODES:
        edges = [
            configuration_logs(
                [
                    p
                    for p in pairs
                    if p["old_generation"] == old and p["new_generation"] == new and p["match_tier"] == "hardware_near"
                ],
                mode,
            )
            for old, new in zip(generations, generations[1:])
        ]
        if any(len(edge) < 3 for edge in edges):
            continue
        keys = sorted(set().union(*(set(e) for e in edges)))
        index = {key: i for i, key in enumerate(keys)}
        weights = np.random.default_rng(seed).multinomial(len(keys), np.full(len(keys), 1 / len(keys)), size=draws)
        logs, valid = [], np.ones(draws, dtype=bool)
        for edge in edges:
            w = weights[:, [index[k] for k in edge]]
            total = w.sum(axis=1)
            valid &= total > 0
            logs.append(np.divide(w @ np.array(list(edge.values())), total, out=np.zeros(draws), where=total > 0))
        samples = np.exp(np.cumsum(np.array(logs).T[valid], axis=1))
        arrays[mode] = samples
        for i, generation in enumerate(generations[1:]):
            rows.append(
                dict(
                    generation=generation,
                    mode=mode,
                    ci95_low=float(np.quantile(samples[:, i], 0.025)),
                    ci95_high=float(np.quantile(samples[:, i], 0.975)),
                    valid_draws=int(valid.sum()),
                    bootstrap_unit="shared_processor_configuration",
                    seed=seed,
                )
            )
    return rows, arrays


def inventory(raw, speed, rate):
    rows = []
    for generation in GENERATIONS:
        source, digest = _checked_bulk(raw / generation / "bulk.csv")
        for track, collected in (("speed", speed), ("rate", rate)):
            benchmark = "CINT" + generation[3:] + ("rate" if track == "rate" else "")
            selected = [r for r in source if r["Benchmark"] == benchmark]
            parallel = Counter((r.get("Parallel") or r.get("Auto Parallelization") or "unknown") for r in selected)
            rows.append(
                dict(
                    generation=generation,
                    track=track,
                    raw_rows=len(selected),
                    usable_rows=len(collected[generation]),
                    base_rows=sum(r.base is not None for r in collected[generation]),
                    peak_rows=sum(r.peak is not None for r in collected[generation]),
                    parallel_flags=json.dumps(dict(parallel), sort_keys=True),
                    copies_field_present=any("copies" in k.lower() for r in selected[:1] for k in r),
                    runtime_threads_field_present=any(
                        k.lower() in {"threads", "# threads", "threads used"} for r in selected[:1] for k in r
                    ),
                    source_sha256=digest,
                )
            )
    return rows


def plot_edges(pairs, fits, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FixedLocator, FuncFormatter, LogLocator, NullFormatter

    generations = ("cpu92", *GENERATIONS)
    for mode in MODES:
        fig, axes = plt.subplots(2, 3, figsize=(16, 9), constrained_layout=True)
        for ax, (old, new) in zip(axes.flat, zip(generations, generations[1:])):
            selected = [p for p in pairs if p["old_generation"] == old and p["new_generation"] == new and p[f"{mode}_ratio"] != ""]
            for tier, color in (("name_cpu_chips_only", "#b6b6b6"), ("hardware_near", "#17628a")):
                subset = [p for p in selected if p["match_tier"] == tier]
                ax.scatter(
                    [p[f"new_{mode}"] for p in subset],
                    [p[f"old_{mode}"] for p in subset],
                    s=12,
                    alpha=0.4,
                    c=color,
                    label="Fit cohort" if tier == "hardware_near" else "Other candidates",
                )
            fit = next(f for f in fits if f["old_generation"] == old and f["new_generation"] == new and f["mode"] == mode)
            if fit.get("factor_old_per_new") and selected:
                x = [min(float(p[f"new_{mode}"]) for p in selected), max(float(p[f"new_{mode}"]) for p in selected)]
                ax.plot(x, [v * fit["factor_old_per_new"] for v in x], c="#20445f")
                ax.fill_between(
                    x,
                    [v * fit["cluster_bootstrap_95_low"] for v in x],
                    [v * fit["cluster_bootstrap_95_high"] for v in x],
                    color="#17628a",
                    alpha=0.15,
                )
            ax.set(
                xscale="log",
                yscale="log",
                xlabel=new + " speed",
                ylabel=old + " speed",
                title=f"{fit['processor_configs']} configs; {fit['status']}",
            )
            ax.grid(alpha=0.2)
            for axis, field in ((ax.xaxis, f"new_{mode}"), (ax.yaxis, f"old_{mode}")):
                values = [float(p[field]) for p in selected]
                axis.set_major_locator(LogLocator(base=10, subs=(1, 2, 5)))
                axis.set_major_formatter(FuncFormatter(lambda v, pos: f"{v:.3g}"))
                axis.set_minor_formatter(NullFormatter())
                if values and max(values) / min(values) < 2:
                    axis.set_major_locator(FixedLocator(np.geomspace(min(values), max(values), 3)))
        axes.flat[-1].axis("off")
        axes.flat[-1].legend(*axes.flat[0].get_legend_handles_labels(), loc="center")
        fig.suptitle(
            f"Integer speed: {mode}; hardware-near fits, all candidate pairs retained\nShading: factor CI95; runtime thread equivalence unverified"
        )
        for ext in ("png", "svg"):
            fig.savefig(output / f"speed-{mode}-overlaps.{ext}", dpi=160)
        plt.close(fig)


def analyze(raw, output, research):
    output.mkdir(parents=True, exist_ok=True)
    research.mkdir(parents=True, exist_ok=True)
    speed, rate = collect_integer(raw, "speed"), collect_integer(raw, "rate")
    speed["cpu92"], audit = collect_speed92(raw)
    rate["cpu92"] = collect_cpu92_rate(Path("data/derived/spec/cpu92-rate/cpu92-rate-records.csv"), raw)
    write_csv(output / "cpu92-speed-parser-audit.csv", audit)
    inv = inventory(raw, speed, rate)
    for track, data in (("speed", speed), ("rate", rate)):
        inv.append(
            dict(
                generation="cpu92",
                track=track,
                usable_rows=len(data["cpu92"]),
                base_rows=sum(r.base is not None for r in data["cpu92"]),
                peak_rows=sum(r.peak is not None for r in data["cpu92"]),
            )
        )
    write_csv(research / "inventory.csv", inv)
    write_csv(
        output / "speed-records.csv",
        [
            {k: json.dumps(v, sort_keys=True) if isinstance(v, dict) else v for k, v in asdict(r).items()}
            for records in speed.values()
            for r in records
        ],
    )
    pairs, fits, chain = [], [], []
    generations = ("cpu92", *GENERATIONS)
    factors = {mode: 1.0 for mode in MODES}
    for old, new in zip(generations, generations[1:]):
        cohort = _automatic_pairs(speed, old, new)
        pairs.extend(cohort)
        for mode in MODES:
            fit = _statistics(cohort, mode, {"hardware_near"})
            fits.append(
                dict(
                    old_generation=old,
                    new_generation=new,
                    mode=mode,
                    candidate_pairings=len(cohort),
                    status="exploratory" if fit else "insufficient_overlap",
                    **(fit or {"processor_configs": 0}),
                )
            )
            factors[mode] = factors[mode] * fit["factor_old_per_new"] if factors[mode] is not None and fit else None
            chain.append(
                dict(
                    generation=new,
                    mode=mode,
                    specint92_equivalent_per_score=factors[mode],
                    status="exploratory" if factors[mode] else "disconnected",
                )
            )
    write_csv(output / "speed-generation-pairs.csv", pairs)
    intervals, samples = chain_intervals(pairs)
    for row in chain:
        interval = next((r for r in intervals if r["generation"] == row["generation"] and r["mode"] == row["mode"]), {})
        row.update(interval)
    np.savez_compressed(output / "speed-chain-draws.npz", **samples)
    write_csv(
        research / "speed-factors.csv",
        [dict(r, processor_family_factors=json.dumps(r.get("processor_family_factors", {}), sort_keys=True)) for r in fits],
    )
    write_csv(research / "speed-chain.csv", chain)
    nonadjacent = []
    for i, old in enumerate(generations):
        for new in generations[i + 2 :]:
            cohort = _automatic_pairs(speed, old, new)
            for mode in MODES:
                fit = _statistics(cohort, mode, {"hardware_near"})
                nonadjacent.append(
                    dict(
                        old_generation=old,
                        new_generation=new,
                        mode=mode,
                        candidate_pairings=len(cohort),
                        status="diagnostic_only" if fit else "insufficient_overlap",
                        **(fit or {"processor_configs": 0}),
                    )
                )
    write_csv(
        research / "speed-nonadjacent.csv",
        [dict(r, processor_family_factors=json.dumps(r.get("processor_family_factors", {}), sort_keys=True)) for r in nonadjacent],
    )
    # Same-generation diagnostics: old/new explicitly mean rate/speed here.
    cross, comparison = [], []
    for generation in generations:
        cohort = _automatic_pairs({"rate": rate[generation], "speed": speed[generation]}, "rate", "speed")
        cross.extend(dict(p, comparison_generation=generation, numerator="rate", denominator="speed") for p in cohort)
        for chips in sorted({int(p["chips"]) for p in cohort}):
            selected = [p for p in cohort if int(p["chips"]) == chips]
            for mode in MODES:
                fit = _statistics(selected, mode, {"hardware_near"})
                comparison.append(
                    dict(
                        generation=generation,
                        chips=chips,
                        mode=mode,
                        candidate_pairings=len(selected),
                        status="diagnostic_only" if fit else "insufficient_overlap",
                        **(fit or {"processor_configs": 0}),
                    )
                )
    write_csv(output / "speed-rate-pairs.csv", cross)
    write_csv(
        research / "speed-rate-diagnostics.csv",
        [dict(r, processor_family_factors=json.dumps(r.get("processor_family_factors", {}), sort_keys=True)) for r in comparison],
    )
    plot_edges(pairs, fits, output)
    report = dict(
        method_version=METHOD,
        code_hashes=code_hashes(__file__),
        output_hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob("*.csv")},
        speed_counts={g: len(speed[g]) for g in generations},
        rate_counts={g: len(rate[g]) for g in generations},
        cpu92_parser_status=dict(Counter(r["status"] for r in audit)),
        pair_count=len(pairs),
        cross_pair_count=len(cross),
        limitations=[
            "Speed is not necessarily single-threaded",
            "Bulk parallel flags are not measured runtime thread counts",
            "Cross-track ratios use native scores, not a universal conversion or core count",
            "Full-chain CI resamples shared configuration keys; unobserved systematic effects remain outside CI",
            "Existing rate outputs and timeline are unchanged",
        ],
        input_hashes={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(raw.glob("*/bulk.csv"))},
    )
    (research / "audit.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


@click.command("compare-tracks")
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/spec/dual-track"), show_default=True)
@click.option("--research-dir", type=click.Path(path_type=Path), default=Path("research/data/spec/dual-track"), show_default=True)
def compare_tracks(raw_dir, output_dir, research_dir):
    """Inventory integer speed/rate, fit speed edges and diagnose same-hardware ratios."""
    try:
        result = analyze(raw_dir, output_dir, research_dir)
    except (OSError, ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, sort_keys=True))
