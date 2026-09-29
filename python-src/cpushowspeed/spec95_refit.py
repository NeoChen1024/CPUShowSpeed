"""CPU95/2000 single-track sensitivity fits using the joint matching policies."""

import hashlib
import json
from pathlib import Path

import click
import numpy as np
from cpushowspeed.research_io import code_hashes, write_csv
from cpushowspeed.spec_joint_tracks import (
    ELIGIBLE_MATCH_TIERS,
    MATCHING_POLICIES,
    match,
)
from cpushowspeed.spec_overlap import _statistics
from cpushowspeed.spec_rate_fit import collect_integer


def run(raw, output, research):
    output.mkdir(parents=True, exist_ok=True)
    research.mkdir(parents=True, exist_ok=True)
    summaries, pairs = [], []
    for track in ("speed", "rate"):
        data = collect_integer(raw, track)
        for policy in MATCHING_POLICIES:
            cohort = match(data["cpu95"], data["cpu2000"], policy)
            pairs.extend(dict(p, track=track, matching_policy=policy) for p in cohort)
            for mode in ("base", "peak"):
                fit = _statistics(cohort, mode, ELIGIBLE_MATCH_TIERS)
                summaries.append(
                    dict(
                        track=track,
                        matching_policy=policy,
                        mode=mode,
                        old_generation="cpu95",
                        new_generation="cpu2000",
                        status="conditional_fit" if fit else "insufficient_configs",
                        **(fit or {}),
                    )
                )
    write_csv(
        research / "single-track-factors.csv",
        [dict(r, processor_family_factors=json.dumps(r.get("processor_family_factors", {}), sort_keys=True)) for r in summaries],
    )
    write_csv(output / "single-track-pairs.csv", pairs)
    plot(summaries, pairs, output)
    audit = dict(
        method_version="95-2000-relaxed-single-track-v1",
        code_hashes=code_hashes(__file__),
        source_sha256={g: hashlib.sha256((raw / g / "bulk.csv").read_bytes()).hexdigest() for g in ("cpu95", "cpu2000")},
        pair_sha256=hashlib.sha256((output / "single-track-pairs.csv").read_bytes()).hexdigest(),
        scope="CPU95/2000 only; independent speed/speed and rate/rate fits; no production factors overwritten",
        interval="existing 10000 configuration bootstrap; different clustering from joint whole-CPU holdouts",
    )
    (research / "single-track-audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    return dict(summary=str(research / "single-track-factors.csv"), rows=len(summaries))


def plot(summaries, pairs, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter

    for mode in ("base", "peak"):
        fig, axes = plt.subplots(2, 3, figsize=(15, 9), constrained_layout=True)
        for i, track in enumerate(("speed", "rate")):
            for j, policy in enumerate(MATCHING_POLICIES):
                ax = axes[i, j]
                rows = [
                    p
                    for p in pairs
                    if p["track"] == track
                    and p["matching_policy"] == policy
                    and p["match_tier"] in ELIGIBLE_MATCH_TIERS
                    and p[f"{mode}_ratio"] != ""
                ]
                fit = next(r for r in summaries if r["track"] == track and r["matching_policy"] == policy and r["mode"] == mode)
                xx = [r[f"new_{mode}"] for r in rows]
                yy = [r[f"old_{mode}"] for r in rows]
                ax.scatter(xx, yy, s=22, alpha=0.55, color="#17628a")
                if rows and fit["status"] == "conditional_fit":
                    x = np.array([min(xx), max(xx)])
                    ax.plot(x, x * fit["factor_old_per_new"], color="#20445f")
                    ax.fill_between(
                        x, x * fit["cluster_bootstrap_95_low"], x * fit["cluster_bootstrap_95_high"], color="#17628a", alpha=0.15
                    )
                ax.set(
                    xscale="log",
                    yscale="log",
                    xlabel=f"CPU2000 {track} {mode}",
                    ylabel=f"CPU95 {track} {mode}",
                    title=f"{policy}: {len(rows)} pairs / {fit.get('processor_configs',0)} configs",
                )
                for axis, values in ((ax.xaxis, xx), (ax.yaxis, yy)):
                    if values:
                        axis.set_major_locator(FixedLocator(np.geomspace(min(values), max(values), 4)))
                        axis.set_major_formatter(FuncFormatter(lambda v, pos: f"{v:.3g}"))
                        axis.set_minor_formatter(NullFormatter())
                ax.grid(alpha=0.2)
        fig.suptitle(
            "CPU95 / CPU2000 independent-track fits\nSame CPU, clock and enabled resources; relaxed policies preserve reported scores. Shading: factor CI95."
        )
        for ext in ("png", "svg"):
            fig.savefig(output / f"single-track-{mode}.{ext}", dpi=160)
        plt.close(fig)


@click.command("refit-95-2000")
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/spec/95-2000-refit"), show_default=True)
@click.option(
    "--research-dir", type=click.Path(path_type=Path), default=Path("research/data/spec/95-2000-refit"), show_default=True
)
def refit_95_2000(raw_dir, output_dir, research_dir):
    """Compare strict, RAM/alias and cross-platform CPU-clock fits for CPU95/2000."""
    try:
        result = run(raw_dir, output_dir, research_dir)
    except (OSError, ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, sort_keys=True))
